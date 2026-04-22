"""seed default system admin

Revision ID: 8aa2656418b8
Revises: ea4ef664efd1
Create Date: 2026-04-22 15:22:07.698895

"""
from typing import Sequence, Union
import os
import uuid

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext


# revision identifiers, used by Alembic.
revision: str = '8aa2656418b8'
down_revision: Union[str, None] = 'ea4ef664efd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def upgrade() -> None:
    bind = op.get_bind()
    system_admin_email = os.getenv("SYSTEM_ADMIN_EMAIL", "systemadmin@urbannest.local")
    system_admin_name = os.getenv("SYSTEM_ADMIN_FULL_NAME", "System Admin")
    # Change this default via environment variable before production deployment.
    system_admin_password = os.getenv("SYSTEM_ADMIN_PASSWORD", "Admin@123")
    hashed_password = pwd_context.hash(system_admin_password)

    bind.execute(
        sa.text(
            """
            INSERT INTO users (id, full_name, email, hashed_password, role)
            VALUES (:id, :full_name, :email, :hashed_password, :role)
            ON CONFLICT (email) DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "full_name": system_admin_name,
            "email": system_admin_email,
            "hashed_password": hashed_password,
            "role": "system_admin",
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    system_admin_email = os.getenv("SYSTEM_ADMIN_EMAIL", "systemadmin@urbannest.local")

    bind.execute(
        sa.text(
            """
            DELETE FROM users
            WHERE email = :email AND role = :role
            """
        ),
        {"email": system_admin_email, "role": "system_admin"},
    )
