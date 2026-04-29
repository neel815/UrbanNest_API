"""add_unit_type_to_units

Revision ID: c3d4e5f6a7b8
Revises: ba950540a77c
Create Date: 2026-04-29 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'ba950540a77c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


unit_type_enum = sa.Enum(
    'studio',
    '1BHK',
    '2BHK',
    '3BHK',
    'penthouse',
    name='unit_type',
    native_enum=False,
)


def upgrade() -> None:
    op.add_column(
        'units',
        sa.Column('unit_type', unit_type_enum, server_default='studio', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('units', 'unit_type')
