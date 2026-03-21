"""Add explicit slot telemetry fields.

Revision ID: 1f4b6d0d8c4a
Revises: ac67284e56b9
Create Date: 2026-03-06 21:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f4b6d0d8c4a"
down_revision = "ac67284e56b9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("parking_slots", sa.Column("last_telemetry_at", sa.DateTime(), nullable=True))
    op.add_column("parking_slots", sa.Column("last_distance_cm", sa.Float(), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE parking_slots
            SET last_telemetry_at = (
                SELECT MAX(occupancy_logs.timestamp)
                FROM occupancy_logs
                WHERE occupancy_logs.slot_id = parking_slots.id
            ),
                last_distance_cm = (
                SELECT occupancy_logs.distance_cm
                FROM occupancy_logs
                WHERE occupancy_logs.slot_id = parking_slots.id
                ORDER BY occupancy_logs.timestamp DESC, occupancy_logs.id DESC
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1
                FROM occupancy_logs
                WHERE occupancy_logs.slot_id = parking_slots.id
            )
            """
        )
    )


def downgrade():
    op.drop_column("parking_slots", "last_distance_cm")
    op.drop_column("parking_slots", "last_telemetry_at")
