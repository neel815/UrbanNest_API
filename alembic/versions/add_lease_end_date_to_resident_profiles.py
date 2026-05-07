"""add_lease_end_date_to_resident_profiles

Revision ID: g1h2i3j4k5l6
Revises: ('25b77d2b58e7', '3c743e153ff6', '443ce5c7c242', '536b4af81e63', 'c3d4e5f6a7b8')
Create Date: 2026-05-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, Sequence[str], None] = ('25b77d2b58e7', '3c743e153ff6', '443ce5c7c242', '536b4af81e63', 'c3d4e5f6a7b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resident_profiles', sa.Column('lease_end_date', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('resident_profiles', 'lease_end_date')
