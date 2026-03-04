"""
PRISM Backend Application Factory
"""
import json
import logging
import os
import secrets
import time
from datetime import timedelta
from uuid import uuid4

from flask import Flask, g, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException

from app.responses import error_response

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def _rate_limit_key() -> str:
    """Return rate-limiting identity based on requester IP."""
    forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address() or "unknown"


limiter = Limiter(key_func=_rate_limit_key, default_limits=[])


def _is_api_path(path: str) -> bool:
    return path.startswith("/api/")


def create_app(config_name=None):
    """Application factory pattern."""
    app = Flask(__name__)

    # Load configuration
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        secret_key = secrets.token_urlsafe(48)
        app.logger.warning(
            "SECRET_KEY not set; generated ephemeral key for this process. "
            "Set SECRET_KEY in environment for stable production security."
        )

    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        jwt_secret = secrets.token_urlsafe(48)
        app.logger.warning(
            "JWT_SECRET_KEY not set; generated ephemeral key for this process. "
            "Set JWT_SECRET_KEY in environment for stable token verification."
        )

    app.config["SECRET_KEY"] = secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///prism_dev.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = jwt_secret
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 24))
    )
    app.config["ALLOW_PUBLIC_READS"] = (
        os.getenv("PRISM_ALLOW_PUBLIC_READS", "false").lower() == "true"
    )
    app.config["ALLOW_PRIVILEGED_SELF_REGISTER"] = (
        os.getenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false").lower() == "true"
    )
    app.config["RATE_LIMIT_AUTH_LOGIN"] = os.getenv("PRISM_RATE_LIMIT_AUTH_LOGIN", "10 per minute")
    app.config["RATE_LIMIT_AUTH_REGISTER"] = os.getenv("PRISM_RATE_LIMIT_AUTH_REGISTER", "5 per minute")
    app.config["RATE_LIMIT_READ_HEAVY"] = os.getenv("PRISM_RATE_LIMIT_READ_HEAVY", "120 per minute")
    app.config["RATE_LIMIT_MUTATION"] = os.getenv("PRISM_RATE_LIMIT_MUTATION", "60 per minute")
    app.config["RATE_LIMIT_SSE"] = os.getenv("PRISM_RATE_LIMIT_SSE", "20 per minute")
    app.config["RATE_LIMIT_CAMERA_UPLOAD"] = os.getenv(
        "PRISM_RATE_LIMIT_CAMERA_UPLOAD",
        "120 per minute",
    )
    app.config["SSE_HEARTBEAT_INTERVAL_SECONDS"] = int(
        os.getenv("PRISM_SSE_HEARTBEAT_INTERVAL_SECONDS", 15)
    )
    app.config["CAMERA_UPLOAD_MAX_BYTES"] = int(
        os.getenv("PRISM_CAMERA_UPLOAD_MAX_BYTES", 2 * 1024 * 1024)
    )
    camera_upload_dir = os.getenv("PRISM_CAMERA_UPLOAD_DIR", "").strip()
    app.config["CAMERA_UPLOAD_DIR"] = camera_upload_dir if camera_upload_dir else None
    app.config["CAMERA_UPLOAD_TOKEN"] = os.getenv("PRISM_CAMERA_UPLOAD_TOKEN", "")

    # Logging baseline
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    app.logger.setLevel(log_level)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    @app.before_request
    def _request_context_setup():
        incoming_request_id = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming_request_id[:128] if incoming_request_id else str(uuid4())
        g.request_id = request_id
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _request_context_teardown(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id

        if _is_api_path(request.path):
            started_at = getattr(g, "request_started_at", None)
            duration_ms = None
            if started_at is not None:
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

            current_user = getattr(g, "current_user", None)
            log_payload = {
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": getattr(current_user, "id", None),
                "role": getattr(current_user, "role", None),
            }
            app.logger.info(json.dumps(log_payload, default=str))

        return response

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):
        if not _is_api_path(request.path):
            return exc
        error_code = None
        if (exc.code or 500) == 429:
            error_code = "rate_limited"
        elif exc.name:
            error_code = exc.name.lower().replace(" ", "_")
        return error_response(
            exc.description or exc.name,
            exc.code or 500,
            code=error_code,
        )

    @app.errorhandler(Exception)
    def _handle_unexpected_exception(exc: Exception):
        if not _is_api_path(request.path):
            raise exc

        app.logger.exception(
            "Unhandled API exception",
            extra={"request_id": getattr(g, "request_id", None)},
        )
        return error_response("Internal server error", 500)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.camera import camera_bp
    from app.routes.health import health_bp
    from app.routes.insights import insights_bp
    from app.routes.lots import lots_bp
    from app.routes.slots import slots_bp
    from app import models  # noqa: F401 - ensure model metadata is loaded

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(camera_bp, url_prefix="/api/v1/camera")
    app.register_blueprint(slots_bp, url_prefix="/api/v1")
    app.register_blueprint(lots_bp, url_prefix="/api/v1")
    app.register_blueprint(insights_bp)

    from seed import register_seed_command

    register_seed_command(app)

    # Optional bootstrap mode for quick local smoke tests without migrations.
    if os.getenv("PRISM_AUTO_CREATE_TABLES", "false").lower() == "true":
        with app.app_context():
            db.create_all()

    return app
