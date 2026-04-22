"""add system admin dashboard fields

Revision ID: 04bdcabb8d2a
Revises: 8aa2656418b8
Create Date: 2026-04-22 16:08:37.013867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04bdcabb8d2a'
down_revision: Union[str, None] = '25b77d2b58e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
