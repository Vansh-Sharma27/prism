"""Shared API response helpers."""

from __future__ import annotations

from flask import g, jsonify

STATUS_CODE_DEFAULTS = {
    400: "bad_request",
    401: "authentication_required",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    429: "rate_limited",
    500: "internal_error",
}


def error_response(
    error: str,
    status_code: int,
    *,
    code: str | None = None,
    details: object | None = None,
):
    """Return a standardized API error payload."""
    payload = {
        "error": error,
        "code": code or STATUS_CODE_DEFAULTS.get(status_code, "error"),
        "request_id": getattr(g, "request_id", None),
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code
