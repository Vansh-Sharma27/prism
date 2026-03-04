"""RBAC helpers for protected API routes."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import g
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models.user import User
from app.responses import error_response


def get_current_user_from_jwt() -> tuple[User | None, object | None]:
    """Resolve current user from JWT identity."""
    identity = get_jwt_identity()
    if identity is None:
        return None, error_response("Authentication required", 401)

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None, error_response("Invalid authentication context", 401)

    user = db.session.get(User, user_id)
    if user is None:
        return None, error_response("User not found", 404)

    g.current_user = user
    return user, None


def require_roles(*allowed_roles: str, error_message: str = "Insufficient role permissions") -> Callable:
    """Decorator that enforces JWT auth + role membership."""
    allowed = {role.lower() for role in allowed_roles}

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user, err = get_current_user_from_jwt()
            if err:
                return err

            if user.role.lower() not in allowed:
                return error_response(error_message, 403)

            return fn(*args, **kwargs)

        return wrapped

    return decorator
