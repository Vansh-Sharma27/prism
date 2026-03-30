"""
Authentication routes for user registration and login.
"""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, limiter
from app.models.user import User
from app.responses import error_response
from app.schemas import user_login_schema, user_register_schema, user_response_schema

auth_bp = Blueprint("auth", __name__)

# Pre-computed hash for constant-time comparison when user is not found (H2 fix)
_DUMMY_HASH = generate_password_hash("timing-equalization-dummy-password")


@auth_bp.route("/register", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_AUTH_REGISTER", "5 per minute"))
def register():
    """Register a new user."""
    try:
        data = user_register_schema.load(request.get_json())
    except ValidationError as err:
        return error_response("Validation failed", 400, code="validation_error", details=err.messages)

    email = data["email"].strip().lower()
    requested_role = data.get("role", "student")
    allow_privileged = current_app.config.get("ALLOW_PRIVILEGED_SELF_REGISTER", False)

    if requested_role != "student" and not allow_privileged:
        return error_response("Self-registration only supports student role", 403, code="forbidden")

    role = requested_role if allow_privileged else "student"

    if User.query.filter_by(email=email).first():
        return error_response("Email already registered", 409, code="conflict")

    user = User(email=email, role=role)
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered", "user": user_response_schema.dump(user)}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_AUTH_LOGIN", "10 per minute"))
def login():
    """Authenticate user and return JWT token."""
    try:
        data = user_login_schema.load(request.get_json())
    except ValidationError as err:
        return error_response("Validation failed", 400, code="validation_error", details=err.messages)

    email = data["email"].strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user:
        # Constant-time comparison to prevent user enumeration via timing (H2)
        check_password_hash(_DUMMY_HASH, data["password"])
        return error_response("Invalid email or password", 401, code="invalid_credentials")

    if user.is_locked:
        return error_response(
            "Account temporarily locked due to repeated failed login attempts",
            429,
            code="account_locked",
        )

    if not user.check_password(data["password"]):
        user.record_failed_login()
        db.session.commit()
        return error_response("Invalid email or password", 401, code="invalid_credentials")

    user.reset_failed_logins()
    access_token = create_access_token(identity=str(user.id))
    db.session.commit()

    return jsonify({"access_token": access_token, "user": user_response_schema.dump(user)}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current authenticated user."""
    user_id = get_jwt_identity()
    try:
        numeric_user_id = int(user_id)
    except (TypeError, ValueError):
        return error_response("Invalid authentication context", 401)

    user = db.session.get(User, numeric_user_id)

    if not user:
        return error_response("User not found", 404)

    return jsonify({"user": user_response_schema.dump(user)}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_AUTH_LOGIN", "10 per minute"))
def logout():
    """Revoke the current access token."""
    jti = get_jwt()["jti"]
    blocklist = current_app.extensions.get("jwt_blocklist")
    if blocklist is not None:
        blocklist.add(jti)
    return jsonify({"message": "Token revoked"}), 200
