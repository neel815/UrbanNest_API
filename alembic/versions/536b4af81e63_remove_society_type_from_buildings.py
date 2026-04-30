"""remove_society_type_from_buildings

Revision ID: 536b4af81e63
Revises: c7c1f6f38c5e
Create Date: 2026-04-30 16:34:18.149554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '536b4af81e63'
down_revision: Union[str, None] = 'c7c1f6f38c5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('buildings', 'society_type')


def downgrade() -> None:
    op.add_column('buildings', sa.Column('society_type', sa.VARCHAR(length=17), server_default=sa.text("'apartment_complex'::character varying"), autoincrement=False, nullable=False))
