"""Add recommendations table for anti-herding tracking.

Revision ID: 3095ed4e6bc9
Revises: 1f4b6d0d8c4a
Create Date: 2026-03-25 07:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3095ed4e6bc9"
down_revision = "1f4b6d0d8c4a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.String(50), sa.ForeignKey("parking_lots.id"), nullable=False),
        sa.Column("zone_id", sa.String(50), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("destination", sa.String(100), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_recommendations_zone_created",
        "recommendations",
        ["zone_id", "created_at"],
    )
    op.create_index(
        "idx_recommendations_lot_created",
        "recommendations",
        ["lot_id", "created_at"],
    )


def downgrade():
    op.drop_index("idx_recommendations_lot_created", table_name="recommendations")
    op.drop_index("idx_recommendations_zone_created", table_name="recommendations")
    op.drop_table("recommendations")
