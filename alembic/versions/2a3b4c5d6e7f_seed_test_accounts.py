"""seed test accounts for admin, resident, and security roles

Revision ID: 2a3b4c5d6e7f
Revises: 1dad97837d39
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = '1dad97837d39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

BUILDING_NAME = 'Skyline Towers'
BUILDING_ADDRESS = '1 Skyline Avenue, UrbanNest'
UNIT_NUMBER = 'A-101'


def _upsert_user(bind, *, email: str, full_name: str, password: str, role: str) -> str:
    hashed_password = pwd_context.hash(password)
    result = bind.execute(
        sa.text(
            """
            INSERT INTO users (id, full_name, email, hashed_password, role, must_reset_password)
            VALUES (:id, :full_name, :email, :hashed_password, :role, false)
            ON CONFLICT (email) DO UPDATE
            SET full_name = EXCLUDED.full_name,
                hashed_password = EXCLUDED.hashed_password,
                role = EXCLUDED.role,
                must_reset_password = false
            RETURNING id
            """
        ),
        {
            'id': str(uuid.uuid4()),
            'full_name': full_name,
            'email': email,
            'hashed_password': hashed_password,
            'role': role,
        },
    )
    return str(result.scalar_one())


def _get_or_create_building(bind) -> str:
    existing_id = bind.execute(
        sa.text('SELECT id FROM buildings WHERE name = :name'),
        {'name': BUILDING_NAME},
    ).scalar_one_or_none()
    if existing_id:
        return str(existing_id)

    building_id = str(uuid.uuid4())
    bind.execute(
        sa.text(
            """
            INSERT INTO buildings (id, name, address, description, building_type, status)
            VALUES (:id, :name, :address, :description, :building_type, :status)
            """
        ),
        {
            'id': building_id,
            'name': BUILDING_NAME,
            'address': BUILDING_ADDRESS,
            'description': 'Seeded building for end-to-end tests',
            'building_type': 'apartment_tower',
            'status': 'active',
        },
    )
    return building_id


def _get_or_create_unit(bind, building_id: str) -> str:
    existing_id = bind.execute(
        sa.text('SELECT id FROM units WHERE building_id = :building_id AND unit_number = :unit_number'),
        {'building_id': building_id, 'unit_number': UNIT_NUMBER},
    ).scalar_one_or_none()
    if existing_id:
        return str(existing_id)

    unit_id = str(uuid.uuid4())
    bind.execute(
        sa.text(
            """
            INSERT INTO units (id, building_id, unit_number, floor, plot_number, status)
            VALUES (:id, :building_id, :unit_number, :floor, :plot_number, :status)
            """
        ),
        {
            'id': unit_id,
            'building_id': building_id,
            'unit_number': UNIT_NUMBER,
            'floor': 1,
            'plot_number': None,
            'status': 'occupied',
        },
    )
    return unit_id


def _upsert_admin_profile(bind, user_id: str, building_id: str) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO admin_profiles (id, user_id, building_id)
            VALUES (:id, :user_id, :building_id)
            ON CONFLICT (user_id) DO UPDATE
            SET building_id = EXCLUDED.building_id
            """
        ),
        {'id': str(uuid.uuid4()), 'user_id': user_id, 'building_id': building_id},
    )


def _upsert_resident_profile(bind, user_id: str, unit_id: str) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO resident_profiles (id, user_id, unit_id)
            VALUES (:id, :user_id, :unit_id)
            ON CONFLICT (user_id) DO UPDATE
            SET unit_id = EXCLUDED.unit_id
            """
        ),
        {'id': str(uuid.uuid4()), 'user_id': user_id, 'unit_id': unit_id},
    )


def _upsert_security_profile(bind, user_id: str, building_id: str) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO security_profiles (id, user_id, badge_number, shift, shift_start_time, shift_end_time, assigned_gate, assigned_building_id, is_active)
            VALUES (:id, :user_id, :badge_number, :shift, :shift_start_time, :shift_end_time, :assigned_gate, :assigned_building_id, true)
            ON CONFLICT (user_id) DO UPDATE
            SET badge_number = EXCLUDED.badge_number,
                shift = EXCLUDED.shift,
                shift_start_time = EXCLUDED.shift_start_time,
                shift_end_time = EXCLUDED.shift_end_time,
                assigned_gate = EXCLUDED.assigned_gate,
                assigned_building_id = EXCLUDED.assigned_building_id,
                is_active = true
            """
        ),
        {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'badge_number': 'SG-001',
            'shift': 'morning',
            'shift_start_time': '06:00',
            'shift_end_time': '14:00',
            'assigned_gate': 'Main Gate',
            'assigned_building_id': building_id,
        },
    )


def upgrade() -> None:
    bind = op.get_bind()

    building_id = _get_or_create_building(bind)
    unit_id = _get_or_create_unit(bind, building_id)

    admin_user_id = _upsert_user(
        bind,
        email='admin@test.com',
        full_name='Admin User',
        password='Admin@123',
        role='admin',
    )
    resident_user_id = _upsert_user(
        bind,
        email='resident@test.com',
        full_name='Resident User',
        password='password123',
        role='resident',
    )
    security_user_id = _upsert_user(
        bind,
        email='security@test.com',
        full_name='Security Guard',
        password='password123',
        role='security',
    )

    _upsert_admin_profile(bind, admin_user_id, building_id)
    _upsert_resident_profile(bind, resident_user_id, unit_id)
    _upsert_security_profile(bind, security_user_id, building_id)


def downgrade() -> None:
    bind = op.get_bind()

    for email in ('admin@test.com', 'resident@test.com', 'security@test.com'):
      bind.execute(sa.text('DELETE FROM security_profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email)'), {'email': email})
      bind.execute(sa.text('DELETE FROM resident_profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email)'), {'email': email})
      bind.execute(sa.text('DELETE FROM admin_profiles WHERE user_id IN (SELECT id FROM users WHERE email = :email)'), {'email': email})
      bind.execute(sa.text('DELETE FROM users WHERE email = :email'), {'email': email})