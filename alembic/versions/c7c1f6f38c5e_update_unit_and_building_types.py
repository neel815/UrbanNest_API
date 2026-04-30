"""update_unit_and_building_types

Revision ID: c7c1f6f38c5e
Revises: c3d4e5f6a7b8
Create Date: 2026-04-30 16:19:13.084067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7c1f6f38c5e'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_unit_type_enum = sa.Enum('studio', '1BHK', '2BHK', '3BHK', 'penthouse', name='unit_type', native_enum=False)
new_unit_type_enum = sa.Enum('flat', 'apartment', 'row_house', 'tenement', 'bungalow', 'villa', 'duplex', 'shop', 'plot', 'other', name='unit_type', native_enum=False)


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE units SET unit_type = 'apartment' WHERE unit_type IN ('studio', '1BHK', '2BHK', '3BHK', 'penthouse')"
        )
    )
    op.alter_column(
        'units',
        'unit_type',
        existing_type=old_unit_type_enum,
        type_=new_unit_type_enum,
        server_default='apartment',
        existing_server_default='studio',
    )
    op.add_column('buildings', sa.Column('society_type', sa.Enum('apartment_complex', 'row_house_society', 'mixed', 'commercial', 'township', name='building_society_type', native_enum=False), server_default='apartment_complex', nullable=False))


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE units SET unit_type = 'studio' WHERE unit_type IN ('flat', 'apartment', 'row_house', 'tenement', 'bungalow', 'villa', 'duplex', 'shop', 'plot', 'other')"
        )
    )
    op.alter_column(
        'units',
        'unit_type',
        existing_type=new_unit_type_enum,
        type_=old_unit_type_enum,
        server_default='studio',
        existing_server_default='apartment',
    )
    op.drop_column('buildings', 'society_type')
