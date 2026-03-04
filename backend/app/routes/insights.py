"""Prediction, recommendation, admin analytics, and notification endpoints."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from queue import Empty
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from flask_jwt_extended import jwt_required
from sqlalchemy import case, func

from app import db, limiter
from app.authz import get_current_user_from_jwt, require_roles
from app.models.parking import OccupancyLog, ParkingEvent, ParkingLot, ParkingSlot, Zone
from app.responses import error_response
from app.services.notifications import broadcaster

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

    zone_rows: list[dict[str, Any]] = []
    for zone in lot.zones.order_by(Zone.name.asc()).all():
        total_slots = zone.slots.count()
        occupied_slots = zone.slots.filter_by(is_occupied=True).count()
        current_pct = round((occupied_slots / total_slots) * 100, 1) if total_slots else 0.0
        zone_rows.append(
            {
                "zone_id": zone.id,
                "name": zone.name,
                "total_slots": total_slots,
                "occupied_slots": occupied_slots,
                "current_occupancy_pct": current_pct,
                "walk_times": zone.walk_times or {},
            }
        )

    return lot, zone_rows


def _prediction_rows(zone_rows: list[dict[str, Any]], day: str, hour: int) -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    day_adjustment = DAY_FACTOR[day]
    hour_adjustment = _time_factor(hour)

    for zone in zone_rows:
        current = zone["current_occupancy_pct"]
        # Skeleton heuristic for Phase 2; real model integration is planned in Phase 3.
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

    return predictions


def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, default=str)}\n\n"


@insights_bp.route("/api/v1/lots/<lot_id>/predict", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_prediction(lot_id: str):
    """Return a mock prediction payload for a lot."""
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

    predictions = _prediction_rows(zone_rows, day=day, hour=hour)
    return jsonify(
        {
            "lot_id": lot.id,
            "lot_name": lot.name,
            "predicted_for": {"day": day, "time": time_label},
            "zones": predictions,
            "model": {
                "status": "mock",
                "version": "day8-skeleton-v1",
                "note": "ML model integration planned in Phase 3.",
            },
        }
    )


@insights_bp.route("/api/v1/lots/<lot_id>/recommend", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_recommendation(lot_id: str):
    """Return a mock zone recommendation for a destination."""
    _, auth_error = get_current_user_from_jwt()
    if auth_error:
        return auth_error

    destination = request.args.get("destination", "").strip()
    if not destination:
        return error_response(
            "destination query parameter is required",
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

    predictions = _prediction_rows(zone_rows, day=day, hour=hour)

    ranked = []
    destination_key = destination.lower()
    for zone, prediction in zip(zone_rows, predictions):
        walk_times = zone.get("walk_times", {})
        walk_min = None
        for key, value in walk_times.items():
            if key.lower() == destination_key:
                walk_min = value
                break
        if walk_min is None:
            walk_min = 8

        score = round(prediction["predicted_occupancy_pct"] + (walk_min * 3), 2)
        ranked.append(
            {
                "zone_id": prediction["zone_id"],
                "name": prediction["name"],
                "predicted_occupancy_pct": prediction["predicted_occupancy_pct"],
                "trend": prediction["trend"],
                "estimated_walk_minutes": walk_min,
                "score": score,
            }
        )

    ranked.sort(key=lambda item: (item["score"], item["predicted_occupancy_pct"]))
    recommendation = ranked[0] if ranked else None

    return jsonify(
        {
            "lot_id": lot.id,
            "lot_name": lot.name,
            "destination": destination,
            "recommended_zone": recommendation,
            "alternatives": ranked[1:3],
            "predicted_for": {"day": day, "time": time_label},
            "engine": {
                "status": "mock",
                "note": "Rule-based recommendation for Day 8. ML ranking is planned for Phase 3.",
            },
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

    latest_ts_subq = (
        db.session.query(
            OccupancyLog.slot_id.label("slot_id"),
            func.max(OccupancyLog.timestamp).label("latest_ts"),
        )
        .group_by(OccupancyLog.slot_id)
        .subquery()
    )

    latest_rows = (
        db.session.query(
            OccupancyLog.slot_id,
            OccupancyLog.timestamp,
            OccupancyLog.distance_cm,
            OccupancyLog.status,
        )
        .join(
            latest_ts_subq,
            (OccupancyLog.slot_id == latest_ts_subq.c.slot_id)
            & (OccupancyLog.timestamp == latest_ts_subq.c.latest_ts),
        )
        .all()
    )
    latest_map = {row.slot_id: row for row in latest_rows}
    slots_seen_24h = {
        slot_id
        for (slot_id,) in (
            db.session.query(OccupancyLog.slot_id)
            .filter(OccupancyLog.timestamp >= uptime_window_start)
            .distinct()
            .all()
        )
    }

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

        latest = latest_map.get(slot.id)
        last_seen = latest.timestamp if latest else None
        is_offline = last_seen is None or last_seen < stale_cutoff

        sensor_row["total_slots"] += 1
        if slot.is_occupied:
            sensor_row["occupied_slots"] += 1
        if is_offline:
            sensor_row["offline_slots"] += 1
        if slot.id in slots_seen_24h:
            sensor_row["slots_seen_24h"] += 1

        if latest and (
            sensor_row["last_seen_at"] is None or latest.timestamp > sensor_row["last_seen_at"]
        ):
            sensor_row["last_seen_at"] = latest.timestamp
            sensor_row["last_distance_cm"] = latest.distance_cm

        sensor_row["slots"].append(
            {
                "slot_id": slot.id,
                "lot_id": slot.lot_id,
                "zone_id": slot.zone_id,
                "slot_number": slot.slot_number,
                "is_occupied": slot.is_occupied,
                "last_seen_at": latest.timestamp.isoformat() if latest else None,
                "last_distance_cm": latest.distance_cm if latest else None,
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

    events = ParkingEvent.query.filter(ParkingEvent.timestamp >= window_start).all()
    hourly_counter: Counter[int] = Counter()
    for event in events:
        if event.timestamp:
            hourly_counter[event.timestamp.hour] += 1

    hourly_distribution = [{"hour": hour, "events": hourly_counter.get(hour, 0)} for hour in range(24)]

    if events:
        peak_hour = max(range(24), key=lambda hour: hourly_counter.get(hour, 0))
        peak_hour_summary = {
            "hour_utc": f"{peak_hour:02d}:00",
            "events": hourly_counter.get(peak_hour, 0),
        }
    else:
        peak_hour_summary = {"hour_utc": None, "events": 0}

    zone_rows = []
    for zone in Zone.query.order_by(Zone.name.asc()).all():
        total_slots = zone.slots.count()
        occupied_slots = zone.slots.filter_by(is_occupied=True).count()
        zone_rows.append(
            {
                "zone_id": zone.id,
                "zone_name": zone.name,
                "lot_id": zone.lot_id,
                "lot_name": zone.lot.name if zone.lot else None,
                "occupied_slots": occupied_slots,
                "total_slots": total_slots,
                "utilization_pct": round((occupied_slots / total_slots) * 100, 1) if total_slots else 0.0,
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

    subscriber_id, queue = broadcaster.subscribe()
    connected_at = datetime.utcnow().isoformat()

    def generate_events():
        try:
            yield _format_sse(
                "connected",
                {
                    "type": "connected",
                    "connected_at": connected_at,
                    "user_id": user.id,
                },
            )
            while True:
                try:
                    event = queue.get(timeout=heartbeat_interval)
                except Empty:
                    yield _format_sse("ping", {"type": "ping", "timestamp": datetime.utcnow().isoformat()})
                    continue

                if lot_filter and event.get("lot_id") != lot_filter:
                    continue

                event_name = str(event.get("type", "message"))
                yield _format_sse(event_name, event)
        finally:
            broadcaster.unsubscribe(subscriber_id)

    response = Response(stream_with_context(generate_events()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response
