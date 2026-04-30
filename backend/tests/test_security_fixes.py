"""Tests for security fixes: CodeQL alerts, Codex findings, and hardening."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db
from app.models.user import MAX_FAILED_LOGINS, User
from seed import seed_campus_data


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "security_fixes.db"
    upload_dir = tmp_path / "camera_uploads"
    upload_dir.mkdir()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "secfix-secret-key-1234567890-abcde")
    monkeypatch.setenv("JWT_SECRET_KEY", "secfix-jwt-secret-key-1234567890")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")
    monkeypatch.setenv("PRISM_CAMERA_UPLOAD_TOKEN", "test-camera-token-xyz")
    monkeypatch.setenv("PRISM_CAMERA_UPLOAD_DIR", str(upload_dir))
    # Lockout/enumeration tests need to exceed MAX_FAILED_LOGINS without
    # tripping the per-IP login rate limiter first.
    monkeypatch.setenv("PRISM_RATE_LIMIT_AUTH_LOGIN", "1000 per minute")
    monkeypatch.setenv("PRISM_RATE_LIMIT_AUTH_REGISTER", "1000 per minute")

    flask_app = create_app()
    flask_app.config.update(TESTING=True)

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

        student = User(email="student@prism.local", role="student")
        student.set_password("Student@12345")
        db.session.add(student)
        db.session.commit()

    return flask_app


@pytest.fixture()
def client(app):
    with app.test_client() as c:
        yield c


def _auth_headers(client, email: str = "admin@prism.local", password: str = "Admin@12345"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


# ────────────────────────────────────────────────────────────────────
# CodeQL HIGH #1 & #2: Path injection in camera.py
# ────────────────────────────────────────────────────────────────────


class TestCameraPathInjection:
    """Verify path traversal is blocked in camera upload endpoint."""

    def _camera_headers(self, camera_id: str = "cam-01"):
        return {
            "X-Camera-Token": "test-camera-token-xyz",
            "X-Camera-ID": camera_id,
            "Content-Type": "image/jpeg",
        }

    def test_normal_upload_succeeds(self, client, app):
        resp = client.post(
            "/api/v1/camera/upload",
            headers=self._camera_headers("cam-01"),
            data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["status"] == "received"
        assert body["camera_id"] == "cam-01"

    def test_rejects_traversal_in_camera_id(self, client):
        """Camera ID with path traversal characters should be rejected by regex."""
        resp = client.post(
            "/api/v1/camera/upload",
            headers=self._camera_headers("../../etc/passwd"),
            data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
        )
        assert resp.status_code == 400

    def test_rejects_slash_in_camera_id(self, client):
        resp = client.post(
            "/api/v1/camera/upload",
            headers=self._camera_headers("cam/bad"),
            data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
        )
        assert resp.status_code == 400

    def test_rejects_null_byte_in_camera_id(self, client):
        resp = client.post(
            "/api/v1/camera/upload",
            headers=self._camera_headers("cam\x00evil"),
            data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
        )
        assert resp.status_code == 400

    def test_saved_file_stays_within_upload_dir(self, client, app):
        """File must be saved inside the configured upload directory."""
        resp = client.post(
            "/api/v1/camera/upload",
            headers=self._camera_headers("legit-cam-01"),
            data=b"\xff\xd8\xff\xe0" + b"\x00" * 50,
        )
        assert resp.status_code == 201
        filename = resp.get_json()["filename"]

        upload_dir = Path(app.config["CAMERA_UPLOAD_DIR"]).resolve()
        saved = upload_dir / filename
        assert saved.exists()
        assert saved.resolve().is_relative_to(upload_dir)


# ────────────────────────────────────────────────────────────────────
# CodeQL MEDIUM #3 & #4: Reflected XSS in insights.py
# ────────────────────────────────────────────────────────────────────


class TestInsightsXSSPrevention:
    """Verify user input in day/time params is sanitized before response."""

    def test_invalid_day_returns_static_error(self, client):
        headers = _auth_headers(client)
        resp = client.get(
            "/api/v1/lots/lot-a/predict?day=<script>alert(1)</script>&time=10:00",
            headers=headers,
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "<script>" not in body["error"]
        assert body["error"] == "Invalid day. Use monday-sunday."

    def test_invalid_time_returns_static_error(self, client):
        headers = _auth_headers(client)
        resp = client.get(
            "/api/v1/lots/lot-a/predict?day=monday&time=<img/onerror=alert(1)>",
            headers=headers,
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "<img" not in body["error"]
        assert body["error"] == "Invalid time. Use HH:MM in 24-hour format."

    def test_valid_time_is_sanitized_in_response(self, client):
        """Even valid time should be reconstructed from parsed ints, not echoed raw."""
        headers = _auth_headers(client)
        resp = client.get(
            "/api/v1/lots/lot-a/predict?day=monday&time=09:30",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["predicted_for"]["time"] == "09:30"

    def test_recommendation_sanitizes_time(self, client):
        headers = _auth_headers(client, "student@prism.local", "Student@12345")
        resp = client.get(
            "/api/v1/lots/lot-a/recommend?destination=Library&day=thursday&time=16:30",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["predicted_for"]["time"] == "16:30"

    def test_xss_in_recommendation_day_rejected(self, client):
        headers = _auth_headers(client, "student@prism.local", "Student@12345")
        resp = client.get(
            '/api/v1/lots/lot-a/recommend?destination=Library&day="><script>&time=10:00',
            headers=headers,
        )
        assert resp.status_code == 400
        assert "<script>" not in resp.get_json()["error"]

    def test_minute_out_of_range_rejected(self, client):
        headers = _auth_headers(client)
        resp = client.get(
            "/api/v1/lots/lot-a/predict?day=monday&time=10:99",
            headers=headers,
        )
        assert resp.status_code == 400


# ────────────────────────────────────────────────────────────────────
# Codex finding: User enumeration via 429 lockout
# ────────────────────────────────────────────────────────────────────


class TestUserEnumerationPrevention:
    """Locked accounts must be indistinguishable from non-existent accounts."""

    def test_locked_account_returns_401_not_429(self, client, app):
        """After lockout, response must be 401 with same message as unknown user."""
        # Trigger lockout by failing MAX_FAILED_LOGINS times
        for _ in range(MAX_FAILED_LOGINS + 1):
            client.post(
                "/api/v1/auth/login",
                json={"email": "student@prism.local", "password": "wrong-password"},
            )

        # Now the account should be locked — verify it returns 401, not 429
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "student@prism.local", "password": "wrong-password"},
        )
        assert resp.status_code == 401
        body = resp.get_json()
        assert body["code"] == "invalid_credentials"
        assert "locked" not in body["error"].lower()

    def test_nonexistent_user_returns_same_response(self, client):
        """Non-existent user should return identical 401 response."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@prism.local", "password": "any-password"},
        )
        assert resp.status_code == 401
        body = resp.get_json()
        assert body["code"] == "invalid_credentials"
        assert body["error"] == "Invalid email or password"

    def test_locked_and_nonexistent_responses_are_identical(self, client, app):
        """Locked account and non-existent user must produce identical responses."""
        # Lock the student account
        for _ in range(MAX_FAILED_LOGINS + 1):
            client.post(
                "/api/v1/auth/login",
                json={"email": "student@prism.local", "password": "wrong"},
            )

        locked_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "student@prism.local", "password": "wrong"},
        )
        nonexistent_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@prism.local", "password": "wrong"},
        )

        assert locked_resp.status_code == nonexistent_resp.status_code == 401

        locked_body = locked_resp.get_json()
        nonexistent_body = nonexistent_resp.get_json()

        assert locked_body["code"] == nonexistent_body["code"]
        assert locked_body["error"] == nonexistent_body["error"]


# ────────────────────────────────────────────────────────────────────
# Security Headers
# ────────────────────────────────────────────────────────────────────


class TestSecurityHeaders:
    """Verify all security response headers are set correctly."""

    def test_api_response_contains_security_headers(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v1/lots", headers=headers)
        assert resp.status_code == 200

        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]
        assert resp.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
        assert resp.headers["Cross-Origin-Opener-Policy"] == "same-origin"
        assert resp.headers["Cross-Origin-Resource-Policy"] == "same-origin"
        assert resp.headers["X-Permitted-Cross-Domain-Policies"] == "none"

    def test_authenticated_api_has_no_cache_headers(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v1/lots", headers=headers)
        assert resp.status_code == 200

        cache_control = resp.headers.get("Cache-Control", "")
        assert "no-store" in cache_control

    def test_request_id_is_returned(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v1/lots", headers=headers)
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) > 0


# ────────────────────────────────────────────────────────────────────
# CORS Configuration
# ────────────────────────────────────────────────────────────────────


class TestCORSConfiguration:
    """Verify CORS is properly restricted."""

    def test_cors_allows_configured_origin(self, client):
        resp = client.options(
            "/api/v1/lots",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"

    def test_cors_rejects_unknown_origin(self, client):
        resp = client.options(
            "/api/v1/lots",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
        assert "evil.com" not in allow_origin


# ────────────────────────────────────────────────────────────────────
# CSRF Mitigation (JSON Content-Type enforcement)
# ────────────────────────────────────────────────────────────────────


class TestCSRFMitigation:
    """Verify JSON content-type enforcement on mutation endpoints."""

    def test_mutation_without_json_content_type_rejected(self, client):
        """POST to API without application/json content-type should be rejected."""
        headers = _auth_headers(client)
        resp = client.post(
            "/api/v1/auth/register",
            data="email=test@test.com&password=Password123",
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 415
        assert resp.get_json()["code"] == "unsupported_media_type"

    def test_mutation_with_json_content_type_accepted(self, client):
        """POST with application/json should work normally."""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "csrf-test@prism.local", "password": "StrongPass123"},
        )
        assert resp.status_code == 201

    def test_get_requests_not_affected_by_content_type_check(self, client):
        """GET requests should work regardless of content-type."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_camera_upload_exempt_from_json_check(self, client):
        """Camera upload uses binary content types and should be exempt."""
        resp = client.post(
            "/api/v1/camera/upload",
            headers={
                "X-Camera-Token": "test-camera-token-xyz",
                "X-Camera-ID": "cam-test",
                "Content-Type": "image/jpeg",
            },
            data=b"\xff\xd8\xff\xe0" + b"\x00" * 100,
        )
        assert resp.status_code == 201


# ────────────────────────────────────────────────────────────────────
# Auth security: lockout still works (just silently)
# ────────────────────────────────────────────────────────────────────


class TestLockoutStillEnforced:
    """Account lockout must still prevent login even though response is 401."""

    def test_correct_password_rejected_when_locked(self, client, app):
        """Even with the right password, locked accounts must not authenticate."""
        # Lock the account
        for _ in range(MAX_FAILED_LOGINS + 1):
            client.post(
                "/api/v1/auth/login",
                json={"email": "student@prism.local", "password": "wrong"},
            )

        # Try with correct password — must still fail
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "student@prism.local", "password": "Student@12345"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["code"] == "invalid_credentials"
