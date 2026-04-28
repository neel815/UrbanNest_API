"""rename profile image url to profile image

Revision ID: c1a2b3c4d5e6
Revises: 7dcf3656996f
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3c4d5e6'
down_revision: Union[str, None] = '7dcf3656996f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'profile_image_url', new_column_name='profile_image')


def downgrade() -> None:
    op.alter_column('users', 'profile_image', new_column_name='profile_image_url')
