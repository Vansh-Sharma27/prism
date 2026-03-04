"""Camera ingest API endpoints."""

from __future__ import annotations

import re
import secrets
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.responses import error_response

camera_bp = Blueprint("camera", __name__)

CAMERA_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _require_ingest_token():
    token = current_app.config.get("CAMERA_UPLOAD_TOKEN", "")
    if not token:
        return None

    supplied = request.headers.get("X-Camera-Token", "")
    if not secrets.compare_digest(supplied, token):
        return error_response(
            "Invalid camera ingest token",
            401,
            code="invalid_credentials",
        )
    return None


def _resolve_upload_dir() -> Path:
    configured_dir = current_app.config.get("CAMERA_UPLOAD_DIR")
    if configured_dir:
        upload_dir = Path(configured_dir)
        if not upload_dir.is_absolute():
            upload_dir = Path(current_app.instance_path) / upload_dir
    else:
        upload_dir = Path(current_app.instance_path) / "camera_uploads"

    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


@camera_bp.route("/upload", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_CAMERA_UPLOAD", "120 per minute"))
def upload_camera_image():
    """Accept camera image frames from ESP32-CAM nodes."""
    token_error = _require_ingest_token()
    if token_error:
        return token_error

    camera_id = request.headers.get("X-Camera-ID", "").strip()
    if not camera_id:
        return error_response(
            "X-Camera-ID header is required",
            400,
            code="validation_error",
        )

    if not CAMERA_ID_PATTERN.fullmatch(camera_id):
        return error_response(
            "Invalid X-Camera-ID format",
            400,
            code="validation_error",
        )

    content_type = request.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    extension = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if extension is None:
        return error_response(
            "Unsupported media type. Use image/jpeg, image/png, or image/webp.",
            415,
            code="unsupported_media_type",
        )

    payload = request.get_data(cache=False, as_text=False)
    if not payload:
        return error_response(
            "Image payload is required",
            400,
            code="validation_error",
        )

    max_bytes = max(1, int(current_app.config.get("CAMERA_UPLOAD_MAX_BYTES", 2 * 1024 * 1024)))
    if len(payload) > max_bytes:
        return error_response(
            f"Image payload exceeds max size of {max_bytes} bytes",
            413,
            code="payload_too_large",
        )

    safe_camera_id = SAFE_FILENAME_PATTERN.sub("-", camera_id)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
    filename = f"{safe_camera_id}_{timestamp}_{secrets.token_hex(3)}{extension}"

    upload_dir = _resolve_upload_dir()
    file_path = upload_dir / filename

    try:
        file_path.write_bytes(payload)
    except OSError:
        current_app.logger.exception(
            "Camera image persist failed | camera_id=%s path=%s",
            camera_id,
            file_path,
        )
        return error_response("Failed to persist camera image", 500)

    return (
        jsonify(
            {
                "status": "received",
                "camera_id": camera_id,
                "filename": filename,
                "bytes_received": len(payload),
                "content_type": content_type,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        ),
        201,
    )
