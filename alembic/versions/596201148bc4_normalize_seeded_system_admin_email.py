"""normalize seeded system admin email

Revision ID: 596201148bc4
Revises: 04bdcabb8d2a
Create Date: 2026-04-22 16:20:57.887578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '596201148bc4'
down_revision: Union[str, None] = '04bdcabb8d2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE users
            SET email = :new_email
            WHERE role = :role AND email = :old_email
            """
        ).bindparams(
            new_email="systemadmin@urbannest.com",
            role="system_admin",
            old_email="systemadmin@urbannest.local",
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE users
            SET email = :old_email
            WHERE role = :role AND email = :new_email
            """
        ).bindparams(
            old_email="systemadmin@urbannest.local",
            role="system_admin",
            new_email="systemadmin@urbannest.com",
        )
    )
