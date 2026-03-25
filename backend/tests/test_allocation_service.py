"""Tests for AllocationService with anti-herding logic."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import create_app, db
from app.models.parking import ParkingSlot, Recommendation, Zone
from app.services.allocation_service import (
    HERDING_PENALTY_PER_REC,
    HERDING_WINDOW_MINUTES,
    WEIGHT_AVAILABILITY,
    WEIGHT_PREDICTION,
    WEIGHT_WALK_DISTANCE,
    AllocationService,
    _build_reason,
    _count_recent_recommendations,
    _resolve_walk_time,
)
from seed import seed_campus_data


@pytest.fixture()
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Flask test client with seeded campus data."""
    db_file = tmp_path / "allocation_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "alloc-test-secret-key-1234567890")
    monkeypatch.setenv("JWT_SECRET_KEY", "alloc-test-jwt-secret-1234567890")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")
    with app.test_client() as c:
        yield c, app


def _auth_headers(client, email: str = "student@gla.ac.in", password: str = "StrongPass123"):
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


class TestResolveWalkTime:
    """Unit tests for _resolve_walk_time helper."""

    def test_exact_match(self):
        assert _resolve_walk_time({"Library": 3, "Cafeteria": 5}, "library") == 3.0

    def test_case_insensitive(self):
        assert _resolve_walk_time({"Admin Block": 5}, "admin block") == 5.0

    def test_default_when_missing(self):
        assert _resolve_walk_time({"Library": 3}, "unknown") == 8.0

    def test_empty_walk_times(self):
        assert _resolve_walk_time({}, "library") == 8.0

    def test_invalid_value_returns_default(self):
        assert _resolve_walk_time({"Library": "invalid"}, "library") == 8.0


class TestBuildReason:
    """Unit tests for _build_reason helper."""

    def test_filling_trend(self):
        reason = _build_reason(
            zone_name="East Wing",
            destination="Library",
            vacant_slots=2,
            total_slots=3,
            walk_min=3.0,
            predicted_pct=75.0,
            trend="filling",
        )
        assert "East Wing" in reason
        assert "2 of 3 slots available" in reason
        assert "3 min walk to Library" in reason
        assert "fill to 75%" in reason

    def test_clearing_trend(self):
        reason = _build_reason(
            zone_name="West Wing",
            destination="Cafeteria",
            vacant_slots=0,
            total_slots=3,
            walk_min=4.0,
            predicted_pct=30.0,
            trend="clearing",
        )
        assert "currently full" in reason
        assert "clear to 30%" in reason

    def test_stable_trend(self):
        reason = _build_reason(
            zone_name="North Deck",
            destination="Lab",
            vacant_slots=1,
            total_slots=3,
            walk_min=2.0,
            predicted_pct=50.0,
            trend="stable",
        )
        assert "stable at 50%" in reason


class TestCountRecentRecommendations:
    """Test anti-herding recommendation counting."""

    def test_no_recommendations_returns_zero(self, app_client):
        _, app = app_client
        with app.app_context():
            count = _count_recent_recommendations("zone-a-east", minutes=5)
            assert count == 0

    def test_counts_recent_recommendations(self, app_client):
        _, app = app_client
        with app.app_context():
            # Add a recent recommendation
            rec = Recommendation(
                lot_id="lot-a",
                zone_id="zone-a-east",
                destination="Library",
                score=75.0,
                created_at=datetime.utcnow(),
            )
            db.session.add(rec)
            db.session.commit()

            count = _count_recent_recommendations("zone-a-east", minutes=5)
            assert count == 1

    def test_ignores_old_recommendations(self, app_client):
        _, app = app_client
        with app.app_context():
            old_rec = Recommendation(
                lot_id="lot-a",
                zone_id="zone-a-east",
                destination="Library",
                score=75.0,
                created_at=datetime.utcnow() - timedelta(minutes=10),
            )
            db.session.add(old_rec)
            db.session.commit()

            count = _count_recent_recommendations("zone-a-east", minutes=5)
            assert count == 0


class TestAllocationServiceRecommend:
    """Integration tests for AllocationService.recommend()."""

    def _make_zone_rows_and_predictions(self, app):
        """Build zone rows and mock predictions from seeded data."""
        with app.app_context():
            zone_rows = []
            for zone in Zone.query.filter_by(lot_id="lot-a").order_by(Zone.name.asc()).all():
                total = zone.slots.count()
                occupied = zone.slots.filter_by(is_occupied=True).count()
                current_pct = round((occupied / total) * 100, 1) if total else 0.0
                zone_rows.append({
                    "zone_id": zone.id,
                    "name": zone.name,
                    "total_slots": total,
                    "occupied_slots": occupied,
                    "current_occupancy_pct": current_pct,
                    "walk_times": zone.walk_times or {},
                })

            predictions = [
                {
                    "zone_id": z["zone_id"],
                    "name": z["name"],
                    "predicted_occupancy_pct": z["current_occupancy_pct"] + 5.0,
                    "trend": "filling",
                    "current_occupancy_pct": z["current_occupancy_pct"],
                    "total_slots": z["total_slots"],
                }
                for z in zone_rows
            ]
            return zone_rows, predictions

    def test_returns_sorted_scores(self, app_client):
        _, app = app_client
        with app.app_context():
            zone_rows, predictions = self._make_zone_rows_and_predictions(app)
            service = AllocationService()
            scores = service.recommend(
                lot_id="lot-a",
                destination="Library",
                zone_rows=zone_rows,
                predictions=predictions,
            )
            assert len(scores) >= 2
            # Verify sorted descending by final_score
            for i in range(len(scores) - 1):
                assert scores[i].final_score >= scores[i + 1].final_score

    def test_scores_are_non_negative(self, app_client):
        _, app = app_client
        with app.app_context():
            zone_rows, predictions = self._make_zone_rows_and_predictions(app)
            service = AllocationService()
            scores = service.recommend(
                lot_id="lot-a",
                destination="Library",
                zone_rows=zone_rows,
                predictions=predictions,
            )
            for s in scores:
                assert s.final_score >= 0.0
                assert s.raw_score >= 0.0

    def test_anti_herding_reduces_score(self, app_client):
        _, app = app_client
        with app.app_context():
            zone_rows, predictions = self._make_zone_rows_and_predictions(app)
            service = AllocationService()

            # First recommendation - no penalty
            scores_first = service.recommend(
                lot_id="lot-a",
                destination="Library",
                zone_rows=zone_rows,
                predictions=predictions,
            )
            first_winner_id = scores_first[0].zone_id
            first_winner_score = scores_first[0].final_score

            # Second recommendation - should have herding penalty on the winner
            scores_second = service.recommend(
                lot_id="lot-a",
                destination="Library",
                zone_rows=zone_rows,
                predictions=predictions,
            )
            # Find the same zone in the second round
            for s in scores_second:
                if s.zone_id == first_winner_id:
                    assert s.herding_penalty > 0.0
                    assert s.final_score < first_winner_score
                    break
            else:
                pytest.fail(f"Zone {first_winner_id} not found in second round scores")

    def test_logs_recommendation_to_db(self, app_client):
        _, app = app_client
        with app.app_context():
            zone_rows, predictions = self._make_zone_rows_and_predictions(app)
            service = AllocationService()
            scores = service.recommend(
                lot_id="lot-a",
                destination="Library",
                zone_rows=zone_rows,
                predictions=predictions,
            )
            # Verify recommendation was persisted
            recs = Recommendation.query.filter_by(lot_id="lot-a").all()
            assert len(recs) == 1
            assert recs[0].zone_id == scores[0].zone_id
            assert recs[0].destination == "Library"

    def test_reason_text_is_generated(self, app_client):
        _, app = app_client
        with app.app_context():
            zone_rows, predictions = self._make_zone_rows_and_predictions(app)
            service = AllocationService()
            scores = service.recommend(
                lot_id="lot-a",
                destination="Library",
                zone_rows=zone_rows,
                predictions=predictions,
            )
            for s in scores:
                assert s.reason
                assert "Library" in s.reason


class TestRecommendEndpoint:
    """Integration tests for the /recommend API endpoint."""

    def test_recommend_returns_200(self, app_client):
        client, _ = app_client
        headers = _auth_headers(client)
        resp = client.get(
            "/api/v1/lots/lot-a/recommend?destination=Library&day=wednesday&time=10:00",
            headers=headers,
        )
        assert resp.status_code == 200

    def test_recommend_response_structure(self, app_client):
        client, _ = app_client
        headers = _auth_headers(client, email="s2@gla.ac.in")
        resp = client.get(
            "/api/v1/lots/lot-a/recommend?destination=Library&day=wednesday&time=10:00",
            headers=headers,
        )
        data = resp.get_json()
        assert data["lot_id"] == "lot-a"
        assert data["destination"] == "Library"
        assert data["engine"]["status"] == "active"
        assert data["engine"]["anti_herding"] is True
        assert "recommended_zone" in data
        assert "alternatives" in data

    def test_recommend_includes_score_and_reason(self, app_client):
        client, _ = app_client
        headers = _auth_headers(client, email="s3@gla.ac.in")
        resp = client.get(
            "/api/v1/lots/lot-a/recommend?destination=Cafeteria&day=monday&time=09:00",
            headers=headers,
        )
        data = resp.get_json()
        rec = data["recommended_zone"]
        assert "score" in rec
        assert "reason" in rec
        assert "herding_penalty" in rec
        assert "availability_pct" in rec
        assert "vacant_slots" in rec

    def test_recommend_requires_destination(self, app_client):
        client, _ = app_client
        headers = _auth_headers(client, email="s4@gla.ac.in")
        resp = client.get(
            "/api/v1/lots/lot-a/recommend?day=wednesday&time=10:00",
            headers=headers,
        )
        assert resp.status_code == 400

    def test_recommend_not_found_lot(self, app_client):
        client, _ = app_client
        headers = _auth_headers(client, email="s5@gla.ac.in")
        resp = client.get(
            "/api/v1/lots/nonexistent/recommend?destination=Library",
            headers=headers,
        )
        assert resp.status_code == 404

    def test_recommend_requires_auth(self, app_client):
        client, _ = app_client
        resp = client.get(
            "/api/v1/lots/lot-a/recommend?destination=Library",
        )
        assert resp.status_code == 401
