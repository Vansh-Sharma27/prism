"""Prediction, recommendation, admin analytics, and notification endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from flask_jwt_extended import jwt_required
from sqlalchemy import case, func

from app import db, limiter
from app.authz import get_current_user_from_jwt, require_roles
from app.models.parking import OccupancyLog, ParkingEvent, ParkingLot, ParkingSlot, Zone
from app.responses import error_response
from app.services.notifications import get_notification_broker

insights_bp = Blueprint("insights", __name__)

VALID_DAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}
DAY_FACTOR = {
    "monday": 3.0,
    "tuesday": 2.0,
    "wednesday": 1.0,
    "thursday": 2.5,
    "friday": 4.0,
    "saturday": -3.0,
    "sunday": -4.0,
}
DAY_NAME_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _time_factor(hour: int) -> float:
    if 8 <= hour <= 10:
        return 12.0
    if 11 <= hour <= 14:
        return 4.0
    if 15 <= hour <= 17:
        return 10.0
    if 18 <= hour <= 20:
        return -2.0
    return -8.0


def _parse_day_and_time() -> tuple[str, str, int] | tuple[None, object, None]:
    day = request.args.get("day", "wednesday").strip().lower()
    time_label = request.args.get("time", "10:00").strip()

    if day not in VALID_DAYS:
        return None, error_response(
            "Invalid day. Use monday-sunday.",
            400,
            code="validation_error",
        ), None

    try:
        hour = int(time_label.split(":")[0])
        if hour < 0 or hour > 23:
            raise ValueError("hour out of range")
    except Exception:
        return None, error_response(
            "Invalid time. Use HH:MM in 24-hour format.",
            400,
            code="validation_error",
        ), None

    return day, time_label, hour


def _lot_zone_snapshot(lot_id: str) -> tuple[ParkingLot | None, list[dict[str, Any]]]:
    lot = db.session.get(ParkingLot, lot_id)
    if lot is None:
        return None, []

    # Single aggregated query replaces 2N individual COUNT queries
    rows = (
        db.session.query(
            Zone.id,
            Zone.name,
            Zone.walk_times,
            func.count(ParkingSlot.id).label("total_slots"),
            func.coalesce(
                func.sum(case((ParkingSlot.is_occupied == True, 1), else_=0)),  # noqa: E712
                0,
            ).label("occupied_slots"),
        )
        .outerjoin(ParkingSlot, ParkingSlot.zone_id == Zone.id)
        .filter(Zone.lot_id == lot_id)
        .group_by(Zone.id, Zone.name, Zone.walk_times)
        .order_by(Zone.name.asc())
        .all()
    )

    zone_rows: list[dict[str, Any]] = []
    for zone_id, name, walk_times, total_slots, occupied_slots in rows:
        total = int(total_slots)
        occupied = int(occupied_slots)
        current_pct = round((occupied / total) * 100, 1) if total else 0.0
        zone_rows.append(
            {
                "zone_id": zone_id,
                "name": name,
                "total_slots": total,
                "occupied_slots": occupied,
                "current_occupancy_pct": current_pct,
                "walk_times": walk_times or {},
            }
        )

    return lot, zone_rows


def _prediction_rows(zone_rows: list[dict[str, Any]], day: str, hour: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Generate predictions using ML model if available, otherwise heuristic fallback.

    Returns (predictions_list, model_metadata_dict).
    """
    from app.services.prediction_service import PredictionService

    service: PredictionService = current_app.extensions.get("prediction_service")

    if service is not None and service.is_available:
        result = _ml_prediction_rows(service, zone_rows, day, hour)
        if result is not None:
            return result

    return _heuristic_prediction_rows(zone_rows, day, hour)


def _zone_previous_occupancy_pct(zone_id: str) -> float | None:
    """Query the average zone occupancy over the last hour from OccupancyLog.

    Returns a float (0-100) or None when no recent history exists.
    This provides a real ``previous_occupancy_pct`` for ML lag features,
    avoiding train/serve skew where lag features collapse to current values.
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    result = (
        db.session.query(
            func.avg(case((OccupancyLog.status == "occupied", 100.0), else_=0.0)),
        )
        .join(ParkingSlot, OccupancyLog.slot_id == ParkingSlot.id)
        .filter(ParkingSlot.zone_id == zone_id)
        .filter(OccupancyLog.timestamp >= one_hour_ago)
        .scalar()
    )
    return round(float(result), 1) if result is not None else None


def _ml_prediction_rows(
    service: Any, zone_rows: list[dict[str, Any]], day: str, hour: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """Produce predictions using the trained ML model.

    Returns None if any zone prediction fails, signalling the caller to
    fall back to heuristic mode so clients never receive silently degraded
    predictions with misleading ``model.status = "active"`` metadata.
    """
    day_index = DAY_NAME_TO_INDEX[day]
    predictions: list[dict[str, Any]] = []

    for zone in zone_rows:
        current = zone["current_occupancy_pct"]
        previous = _zone_previous_occupancy_pct(zone["zone_id"])
        predicted = service.predict(
            target_hour=hour,
            target_day_of_week=day_index,
            current_occupancy_pct=current,
            previous_occupancy_pct=previous,
        )
        if predicted is None:
            return None
        trend = service.compute_trend(
            current_occupancy_pct=current,
            predicted_occupancy_pct=predicted,
        )

        predictions.append(
            {
                "zone_id": zone["zone_id"],
                "name": zone["name"],
                "predicted_occupancy_pct": predicted,
                "trend": trend,
                "current_occupancy_pct": current,
                "total_slots": zone["total_slots"],
            }
        )

    model_meta = {
        "status": "active",
        "version": "day15-rf-v1",
        "type": "RandomForest",
    }
    return predictions, model_meta


def _heuristic_prediction_rows(
    zone_rows: list[dict[str, Any]], day: str, hour: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fallback heuristic predictions when ML model is unavailable."""
    predictions: list[dict[str, Any]] = []
    day_adjustment = DAY_FACTOR[day]
    hour_adjustment = _time_factor(hour)

    for zone in zone_rows:
        current = zone["current_occupancy_pct"]
        predicted = max(0.0, min(100.0, round(current + day_adjustment + hour_adjustment, 1)))
        if predicted >= current + 5:
            trend = "filling"
        elif predicted <= current - 5:
            trend = "clearing"
        else:
            trend = "stable"

        predictions.append(
            {
                "zone_id": zone["zone_id"],
                "name": zone["name"],
                "predicted_occupancy_pct": predicted,
                "trend": trend,
                "current_occupancy_pct": current,
                "total_slots": zone["total_slots"],
            }
        )

    model_meta = {
        "status": "heuristic_fallback",
        "version": "day8-skeleton-v1",
        "note": "ML model not loaded; using rule-based heuristic.",
    }
    return predictions, model_meta


def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
    safe_event = event_name.replace("\n", "").replace("\r", "")
    return f"event: {safe_event}\ndata: {json.dumps(payload, default=str)}\n\n"


@insights_bp.route("/api/v1/lots/<lot_id>/predict", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_prediction(lot_id: str):
    """Return ML-backed or heuristic prediction payload for a lot."""
    _, auth_error = get_current_user_from_jwt()
    if auth_error:
        return auth_error

    parsed = _parse_day_and_time()
    if parsed[0] is None:
        return parsed[1]
    day, time_label, hour = parsed

    lot, zone_rows = _lot_zone_snapshot(lot_id)
    if lot is None:
        return error_response("Lot not found", 404)

    predictions, model_meta = _prediction_rows(zone_rows, day=day, hour=hour)
    return jsonify(
        {
            "lot_id": lot.id,
            "lot_name": lot.name,
            "predicted_for": {"day": day, "time": time_label},
            "zones": predictions,
            "model": model_meta,
        }
    )


@insights_bp.route("/api/v1/lots/<lot_id>/recommend", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_recommendation(lot_id: str):
    """Return ML-ranked zone recommendation with anti-herding."""
    user, auth_error = get_current_user_from_jwt()
    if auth_error:
        return auth_error

    destination = request.args.get("destination", "").strip()
    if not destination or len(destination) > 100:
        return error_response(
            "destination query parameter is required (max 100 characters)",
            400,
            code="validation_error",
        )

    parsed = _parse_day_and_time()
    if parsed[0] is None:
        return parsed[1]
    day, time_label, hour = parsed

    lot, zone_rows = _lot_zone_snapshot(lot_id)
    if lot is None:
        return error_response("Lot not found", 404)

    predictions, model_meta = _prediction_rows(zone_rows, day=day, hour=hour)

    from app.services.allocation_service import AllocationService

    allocation = AllocationService()
    scored_zones = allocation.recommend(
        lot_id=lot_id,
        destination=destination,
        zone_rows=zone_rows,
        predictions=predictions,
        user_id=user.id if user else None,
    )

    def _zone_to_dict(z):
        return {
            "zone_id": z.zone_id,
            "name": z.zone_name,
            "predicted_occupancy_pct": z.predicted_occupancy_pct,
            "trend": z.trend,
            "estimated_walk_minutes": z.walk_minutes,
            "availability_pct": z.availability_pct,
            "vacant_slots": z.vacant_slots,
            "total_slots": z.total_slots,
            "score": z.final_score,
            "herding_penalty": z.herding_penalty,
            "reason": z.reason,
        }

    recommendation = _zone_to_dict(scored_zones[0]) if scored_zones else None
    alternatives = [_zone_to_dict(z) for z in scored_zones[1:3]]

    return jsonify(
        {
            "lot_id": lot.id,
            "lot_name": lot.name,
            "destination": destination,
            "recommended_zone": recommendation,
            "alternatives": alternatives,
            "predicted_for": {"day": day, "time": time_label},
            "engine": {
                "status": "active",
                "version": "allocation-v1",
                "weights": {
                    "availability": 0.40,
                    "walk_distance": 0.35,
                    "prediction": 0.25,
                },
                "anti_herding": True,
            },
            "model": model_meta,
        }
    )


@insights_bp.route("/api/admin/sensors", methods=["GET"])
@insights_bp.route("/api/v1/admin/sensors", methods=["GET"])
@require_roles("admin", error_message="Admin access required")
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_admin_sensors():
    """Return sensor fleet health summary for admin dashboards."""
    offline_after_seconds = request.args.get("offline_after_seconds", 90, type=int)
    offline_after_seconds = max(30, min(offline_after_seconds, 600))
    stale_cutoff = datetime.utcnow() - timedelta(seconds=offline_after_seconds)
    uptime_window_start = datetime.utcnow() - timedelta(hours=24)

    sensors: dict[str, dict[str, Any]] = {}
    for slot in ParkingSlot.query.order_by(ParkingSlot.sensor_id.asc(), ParkingSlot.slot_number.asc()).all():
        sensor_id = slot.sensor_id or f"{slot.lot_id}-sensor-{slot.slot_number}"
        sensor_row = sensors.get(sensor_id)
        if sensor_row is None:
            sensor_row = {
                "sensor_id": sensor_id,
                "total_slots": 0,
                "occupied_slots": 0,
                "offline_slots": 0,
                "last_seen_at": None,
                "last_distance_cm": None,
                "status": "offline",
                "slots_seen_24h": 0,
                "slots": [],
            }
            sensors[sensor_id] = sensor_row

        last_seen = slot.last_telemetry_at
        is_offline = last_seen is None or last_seen < stale_cutoff

        sensor_row["total_slots"] += 1
        if slot.is_occupied:
            sensor_row["occupied_slots"] += 1
        if is_offline:
            sensor_row["offline_slots"] += 1
        if last_seen and last_seen >= uptime_window_start:
            sensor_row["slots_seen_24h"] += 1

        if last_seen and (
            sensor_row["last_seen_at"] is None or last_seen > sensor_row["last_seen_at"]
        ):
            sensor_row["last_seen_at"] = last_seen
            sensor_row["last_distance_cm"] = slot.last_distance_cm

        sensor_row["slots"].append(
            {
                "slot_id": slot.id,
                "lot_id": slot.lot_id,
                "zone_id": slot.zone_id,
                "slot_number": slot.slot_number,
                "is_occupied": slot.is_occupied,
                "last_seen_at": last_seen.isoformat() if last_seen else None,
                "last_distance_cm": slot.last_distance_cm,
                "telemetry_status": "offline" if is_offline else "online",
            }
        )

    sensor_list: list[dict[str, Any]] = []
    for row in sensors.values():
        if row["offline_slots"] == row["total_slots"]:
            row["status"] = "offline"
        elif row["offline_slots"] > 0:
            row["status"] = "degraded"
        else:
            row["status"] = "online"

        row["uptime_24h_pct"] = round(
            (row["slots_seen_24h"] / row["total_slots"] * 100) if row["total_slots"] else 0.0,
            1,
        )
        row.pop("slots_seen_24h", None)
        row["last_seen_at"] = row["last_seen_at"].isoformat() if row["last_seen_at"] else None
        sensor_list.append(row)

    sensor_list.sort(key=lambda item: item["sensor_id"])
    total_sensors = len(sensor_list)
    offline_sensors = sum(1 for row in sensor_list if row["status"] == "offline")
    degraded_sensors = sum(1 for row in sensor_list if row["status"] == "degraded")

    return jsonify(
        {
            "sensors": sensor_list,
            "summary": {
                "total_sensors": total_sensors,
                "online_sensors": total_sensors - offline_sensors - degraded_sensors,
                "degraded_sensors": degraded_sensors,
                "offline_sensors": offline_sensors,
                "offline_threshold_seconds": offline_after_seconds,
            },
        }
    )


@insights_bp.route("/api/admin/analytics", methods=["GET"])
@insights_bp.route("/api/v1/admin/analytics", methods=["GET"])
@require_roles("admin", error_message="Admin access required")
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_admin_analytics():
    """Return historical analytics summary for admin dashboards."""
    days = request.args.get("days", 7, type=int)
    days = max(1, min(days, 30))
    window_start = datetime.utcnow() - timedelta(days=days)

    daily_rows = (
        db.session.query(
            func.date(OccupancyLog.timestamp).label("day"),
            func.avg(
                case(
                    (OccupancyLog.status == "occupied", 1.0),
                    else_=0.0,
                )
            ).label("occupied_ratio"),
            func.count(OccupancyLog.id).label("samples"),
        )
        .filter(OccupancyLog.timestamp >= window_start)
        .group_by(func.date(OccupancyLog.timestamp))
        .order_by(func.date(OccupancyLog.timestamp))
        .all()
    )

    daily_occupancy_average = [
        {
            "date": str(row.day),
            "avg_occupancy_pct": round(float(row.occupied_ratio or 0.0) * 100, 1),
            "samples": int(row.samples or 0),
        }
        for row in daily_rows
    ]

    # Hourly event distribution via SQL aggregate (avoids loading all rows into memory)
    hourly_rows = (
        db.session.query(
            func.extract("hour", ParkingEvent.timestamp).label("hour"),
            func.count(ParkingEvent.id).label("cnt"),
        )
        .filter(ParkingEvent.timestamp >= window_start)
        .filter(ParkingEvent.timestamp.isnot(None))
        .group_by(func.extract("hour", ParkingEvent.timestamp))
        .all()
    )
    hourly_counter: dict[int, int] = {int(row.hour): int(row.cnt) for row in hourly_rows}

    hourly_distribution = [{"hour": hour, "events": hourly_counter.get(hour, 0)} for hour in range(24)]

    if hourly_counter:
        peak_hour = max(range(24), key=lambda hour: hourly_counter.get(hour, 0))
        peak_hour_summary = {
            "hour_utc": f"{peak_hour:02d}:00",
            "events": hourly_counter.get(peak_hour, 0),
        }
    else:
        peak_hour_summary = {"hour_utc": None, "events": 0}

    # Zone utilization: single aggregated query (replaces 2N COUNT queries + lazy lot load)
    zone_util_rows = (
        db.session.query(
            Zone.id,
            Zone.name,
            Zone.lot_id,
            ParkingLot.name.label("lot_name"),
            func.count(ParkingSlot.id).label("total_slots"),
            func.coalesce(
                func.sum(case((ParkingSlot.is_occupied == True, 1), else_=0)),  # noqa: E712
                0,
            ).label("occupied_slots"),
        )
        .join(ParkingLot, ParkingLot.id == Zone.lot_id)
        .outerjoin(ParkingSlot, ParkingSlot.zone_id == Zone.id)
        .group_by(Zone.id, Zone.name, Zone.lot_id, ParkingLot.name)
        .order_by(Zone.name.asc())
        .all()
    )

    zone_rows = []
    for zone_id, zone_name, lot_id, lot_name, total_slots, occupied_slots in zone_util_rows:
        total = int(total_slots)
        occupied = int(occupied_slots)
        zone_rows.append(
            {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "lot_id": lot_id,
                "lot_name": lot_name,
                "occupied_slots": occupied,
                "total_slots": total,
                "utilization_pct": round((occupied / total) * 100, 1) if total else 0.0,
            }
        )

    zone_rows.sort(key=lambda item: item["utilization_pct"], reverse=True)

    return jsonify(
        {
            "window_days": days,
            "daily_occupancy_average": daily_occupancy_average,
            "peak_hour": peak_hour_summary,
            "hourly_event_distribution": hourly_distribution,
            "zone_utilization_comparison": zone_rows,
            "generated_at": datetime.utcnow().isoformat(),
        }
    )


@insights_bp.route("/api/notifications/stream", methods=["GET"])
@insights_bp.route("/api/v1/notifications/stream", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_SSE", "20 per minute"))
def stream_notifications():
    """Stream live slot-change notifications over SSE for authenticated users."""
    user, auth_error = get_current_user_from_jwt()
    if auth_error:
        return auth_error

    lot_filter = request.args.get("lot_id", "").strip() or None
    heartbeat_interval = max(5, int(current_app.config.get("SSE_HEARTBEAT_INTERVAL_SECONDS", 15)))
    max_duration_seconds = max(60, int(current_app.config.get("SSE_MAX_DURATION_SECONDS", 1800)))

    subscription = get_notification_broker().subscribe()
    connected_at = datetime.utcnow()

    def generate_events():
        try:
            yield _format_sse(
                "connected",
                {
                    "type": "connected",
                    "connected_at": connected_at.isoformat(),
                    "user_id": user.id,
                    "max_duration_seconds": max_duration_seconds,
                },
            )
            while True:
                # P2 fix: enforce max-duration cap to prevent indefinite connections
                elapsed = (datetime.utcnow() - connected_at).total_seconds()
                if elapsed >= max_duration_seconds:
                    yield _format_sse(
                        "reconnect",
                        {
                            "type": "reconnect",
                            "reason": "max_duration_exceeded",
                            "elapsed_seconds": int(elapsed),
                        },
                    )
                    break

                event = subscription.get(timeout=heartbeat_interval)
                if event is None:
                    yield _format_sse("ping", {"type": "ping", "timestamp": datetime.utcnow().isoformat()})
                    continue

                if lot_filter and event.get("lot_id") != lot_filter:
                    continue

                event_name = str(event.get("type", "message"))
                yield _format_sse(event_name, event)
        finally:
            subscription.close()

    response = Response(stream_with_context(generate_events()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response
