"""AllocationService for ML-ranked zone recommendations with anti-herding.

Scores zones by availability (40%), walking distance (35%), and ML-predicted
future occupancy (25%). Applies a decaying penalty when a zone has been
recommended too often in the recent window, spreading demand across zones.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from app import db
from app.models.parking import Recommendation

logger = logging.getLogger(__name__)

# Scoring weights (must sum to 1.0)
WEIGHT_AVAILABILITY = 0.40
WEIGHT_WALK_DISTANCE = 0.35
WEIGHT_PREDICTION = 0.25

# Anti-herding: penalty per recent recommendation in the window
HERDING_PENALTY_PER_REC = 5.0
HERDING_WINDOW_MINUTES = 5

# Walk-distance scoring: zones beyond this threshold score 0
MAX_WALK_MINUTES = 15


@dataclass(frozen=True)
class ZoneScore:
    """Immutable container for a scored zone recommendation."""

    zone_id: str
    zone_name: str
    lot_id: str
    availability_pct: float
    walk_minutes: float
    predicted_occupancy_pct: float
    trend: str
    herding_penalty: float
    raw_score: float
    final_score: float
    total_slots: int
    vacant_slots: int
    reason: str


class AllocationService:
    """Computes zone recommendations with anti-herding logic.

    Instance is stateless; all state comes from the database and the
    prediction service passed at call time.
    """

    def recommend(
        self,
        *,
        lot_id: str,
        destination: str,
        zone_rows: list[dict[str, Any]],
        predictions: list[dict[str, Any]],
        user_id: int | None = None,
    ) -> list[ZoneScore]:
        """Return zones ranked by composite score (best first).

        Args:
            lot_id: Parking lot identifier.
            destination: Target building/location short code.
            zone_rows: Zone snapshot dicts from _lot_zone_snapshot().
            predictions: Prediction dicts matching zone_rows ordering.
            user_id: Authenticated user id (optional, for logging).

        Returns:
            List of ZoneScore sorted by final_score descending.
        """
        destination_key = destination.lower()

        # Batch-fetch recent recommendation counts per zone (eliminates N+1)
        zone_ids = [z["zone_id"] for z in zone_rows]
        herding_counts = _batch_count_recent_recommendations(
            zone_ids, minutes=HERDING_WINDOW_MINUTES
        )

        scores: list[ZoneScore] = []

        for zone_data, pred in zip(zone_rows, predictions):
            zone_id = zone_data["zone_id"]
            total_slots = zone_data["total_slots"]
            occupied_slots = zone_data["occupied_slots"]
            vacant_slots = total_slots - occupied_slots

            # 1. Availability score (0-100): higher is better
            availability_pct = (
                round((vacant_slots / total_slots) * 100, 1)
                if total_slots > 0
                else 0.0
            )

            # 2. Walk-distance score (0-100): lower walk time -> higher score
            walk_times = zone_data.get("walk_times", {})
            walk_min = _resolve_walk_time(walk_times, destination_key)
            walk_score = max(0.0, round((1.0 - walk_min / MAX_WALK_MINUTES) * 100, 1))

            # 3. Prediction score (0-100): lower predicted occupancy -> higher score
            predicted_pct = pred["predicted_occupancy_pct"]
            prediction_score = round(100.0 - predicted_pct, 1)

            # Composite raw score
            raw_score = round(
                WEIGHT_AVAILABILITY * availability_pct
                + WEIGHT_WALK_DISTANCE * walk_score
                + WEIGHT_PREDICTION * prediction_score,
                2,
            )

            # Anti-herding penalty (from batch query)
            recent_count = herding_counts.get(zone_id, 0)
            herding_penalty = round(recent_count * HERDING_PENALTY_PER_REC, 2)
            final_score = round(max(0.0, raw_score - herding_penalty), 2)

            reason = _build_reason(
                zone_name=zone_data["name"],
                destination=destination,
                vacant_slots=vacant_slots,
                total_slots=total_slots,
                walk_min=walk_min,
                predicted_pct=predicted_pct,
                trend=pred["trend"],
            )

            scores.append(
                ZoneScore(
                    zone_id=zone_id,
                    zone_name=zone_data["name"],
                    lot_id=lot_id,
                    availability_pct=availability_pct,
                    walk_minutes=walk_min,
                    predicted_occupancy_pct=predicted_pct,
                    trend=pred["trend"],
                    herding_penalty=herding_penalty,
                    raw_score=raw_score,
                    final_score=final_score,
                    total_slots=total_slots,
                    vacant_slots=vacant_slots,
                    reason=reason,
                )
            )

        scores.sort(key=lambda s: s.final_score, reverse=True)

        # Log the top recommendation for audit
        if scores:
            _log_recommendation(
                lot_id=lot_id,
                zone_id=scores[0].zone_id,
                destination=destination,
                score=scores[0].final_score,
                user_id=user_id,
            )

        return scores


def _resolve_walk_time(walk_times: dict[str, Any], destination_key: str) -> float:
    """Case-insensitive lookup of walking time; defaults to 8 minutes."""
    for key, value in walk_times.items():
        if key.lower() == destination_key:
            try:
                return float(value)
            except (TypeError, ValueError):
                return 8.0
    return 8.0


def _batch_count_recent_recommendations(
    zone_ids: list[str], minutes: int
) -> dict[str, int]:
    """Count recent recommendations for multiple zones in a single query."""
    if not zone_ids:
        return {}

    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    rows = (
        db.session.query(
            Recommendation.zone_id,
            func.count(Recommendation.id),
        )
        .filter(Recommendation.zone_id.in_(zone_ids))
        .filter(Recommendation.created_at >= cutoff)
        .group_by(Recommendation.zone_id)
        .all()
    )
    return {zone_id: int(count) for zone_id, count in rows}


# Retention: prune recommendations older than this to prevent unbounded growth
RETENTION_HOURS = 24
_PRUNE_BATCH_SIZE = 500


def _log_recommendation(
    *,
    lot_id: str,
    zone_id: str,
    destination: str,
    score: float,
    user_id: int | None,
) -> None:
    """Persist the winning recommendation for anti-herding tracking."""
    try:
        rec = Recommendation(
            lot_id=lot_id,
            zone_id=zone_id,
            user_id=user_id,
            destination=destination,
            score=score,
        )
        db.session.add(rec)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception(
            "Failed to log recommendation | lot_id=%s zone_id=%s", lot_id, zone_id
        )
        return

    # Prune old recommendations to prevent unbounded table growth (H3 fix)
    try:
        cutoff = datetime.utcnow() - timedelta(hours=RETENTION_HOURS)
        # Two-step delete: select IDs first, then delete (limit + delete is invalid in SQLAlchemy)
        stale_ids = (
            db.session.query(Recommendation.id)
            .filter(Recommendation.created_at < cutoff)
            .limit(_PRUNE_BATCH_SIZE)
            .all()
        )
        if stale_ids:
            id_list = [row[0] for row in stale_ids]
            deleted = (
                Recommendation.query
                .filter(Recommendation.id.in_(id_list))
                .delete(synchronize_session=False)
            )
            db.session.commit()
            logger.info("Pruned %d old recommendations (older than %dh)", deleted, RETENTION_HOURS)
    except Exception:
        db.session.rollback()
        logger.exception("Failed to prune old recommendations")


def _build_reason(
    *,
    zone_name: str,
    destination: str,
    vacant_slots: int,
    total_slots: int,
    walk_min: float,
    predicted_pct: float,
    trend: str,
) -> str:
    """Generate a human-readable recommendation reason."""
    parts = []

    if vacant_slots > 0:
        parts.append(f"{vacant_slots} of {total_slots} slots available")
    else:
        parts.append("currently full")

    parts.append(f"{walk_min:.0f} min walk to {destination}")

    if trend == "filling":
        parts.append(f"predicted to fill to {predicted_pct:.0f}%")
    elif trend == "clearing":
        parts.append(f"predicted to clear to {predicted_pct:.0f}%")
    else:
        parts.append(f"predicted stable at {predicted_pct:.0f}%")

    return f"{zone_name}: {'; '.join(parts)}."
