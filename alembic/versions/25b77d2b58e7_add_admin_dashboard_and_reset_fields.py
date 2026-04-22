"""add admin dashboard and reset fields

Revision ID: 25b77d2b58e7
Revises: 8aa2656418b8
Create Date: 2026-04-22 15:59:08.117509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "25b77d2b58e7"
down_revision: Union[str, None] = "8aa2656418b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_image_url", sa.String(length=500), nullable=True))
    op.add_column(
        "users",
        sa.Column("must_reset_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("reset_token", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_users_reset_token", "users", ["reset_token"])


def downgrade() -> None:
    op.drop_constraint("uq_users_reset_token", "users", type_="unique")
    op.drop_column("users", "reset_token_expires_at")
    op.drop_column("users", "reset_token")
    op.drop_column("users", "must_reset_password")
    op.drop_column("users", "profile_image_url")
