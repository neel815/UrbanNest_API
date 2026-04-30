"""fix_maintenance_units_to_vacant

Revision ID: 83d9dc687acb
Revises: 6132749abee1
Create Date: 2026-04-30 17:38:25.478428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83d9dc687acb'
down_revision: Union[str, None] = '6132749abee1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert maintenance units to vacant (these are placeholder units from initial setup)
    op.execute(sa.text("UPDATE units SET status = 'vacant' WHERE status = 'maintenance'"))


def downgrade() -> None:
    # Convert vacant units back to maintenance (only for units without residents)
    op.execute(sa.text("UPDATE units SET status = 'maintenance' WHERE status = 'vacant' AND id NOT IN (SELECT unit_id FROM resident_profiles WHERE unit_id IS NOT NULL)"))
