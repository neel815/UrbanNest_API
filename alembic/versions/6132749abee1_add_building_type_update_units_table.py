"""add_building_type_update_units_table

Revision ID: 6132749abee1
Revises: 536b4af81e63
Create Date: 2026-04-30 16:57:14.870885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6132749abee1'
down_revision: Union[str, None] = '536b4af81e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('buildings', sa.Column('building_type', sa.Enum('apartment_tower', 'row_house_tenement', 'bungalow', 'villa', name='building_type', native_enum=False), server_default='apartment_tower', nullable=False))
    op.add_column('units', sa.Column('floor', sa.Integer(), nullable=True))
    op.add_column('units', sa.Column('plot_number', sa.String(length=50), nullable=True))
    op.execute(sa.text("UPDATE units SET floor = floor_number WHERE floor_number IS NOT NULL"))
    op.execute(sa.text("UPDATE units SET status = 'vacant' WHERE status = 'available'"))
    op.alter_column('units', 'status', existing_type=sa.Enum('vacant', 'occupied', 'maintenance', name='unit_status', native_enum=False), server_default='vacant', existing_server_default='available')
    op.drop_column('units', 'floor_number')
    op.drop_column('units', 'size_sqft')
    op.drop_column('units', 'unit_type')


def downgrade() -> None:
    op.alter_column('units', 'status', existing_type=sa.Enum('vacant', 'occupied', 'maintenance', name='unit_status', native_enum=False), server_default='available', existing_server_default='vacant')
    op.execute(sa.text("UPDATE units SET status = 'available' WHERE status = 'vacant'"))
    op.add_column('units', sa.Column('size_sqft', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('units', sa.Column('floor_number', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('units', sa.Column('unit_type', sa.VARCHAR(length=9), server_default=sa.text("'apartment'::character varying"), autoincrement=False, nullable=False))
    op.execute(sa.text("UPDATE units SET floor_number = floor WHERE floor IS NOT NULL"))
    op.drop_column('units', 'plot_number')
    op.drop_column('units', 'floor')
    op.drop_column('buildings', 'building_type')
