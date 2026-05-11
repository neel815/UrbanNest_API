"""add_patrol_route_metadata

Revision ID: b1f7d8c9e0a1
Revises: e8461c6a7bb4
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1f7d8c9e0a1"
down_revision: Union[str, None] = "e8461c6a7bb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patrol_routes", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "patrol_routes",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "patrol_routes",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "patrol_routes",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("patrol_routes", "updated_at")
    op.drop_column("patrol_routes", "created_at")
    op.drop_column("patrol_routes", "is_active")
    op.drop_column("patrol_routes", "description")
