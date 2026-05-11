"""add_patrol_round_checkpoints

Revision ID: c2d3e4f5a6b7
Revises: b1f7d8c9e0a1
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1f7d8c9e0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patrol_rounds", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "patrol_rounds",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "patrol_rounds",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "patrol_round_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("round_id", sa.UUID(), nullable=False),
        sa.Column("checkpoint_id", sa.UUID(), nullable=False),
        sa.Column("checkpoint_name", sa.String(length=200), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_visited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["round_id"], ["patrol_rounds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("round_id", "checkpoint_id", name="uq_patrol_round_checkpoint"),
    )
    op.create_index(op.f("ix_patrol_round_checkpoints_round_id"), "patrol_round_checkpoints", ["round_id"], unique=False)
    op.create_index(op.f("ix_patrol_round_checkpoints_checkpoint_id"), "patrol_round_checkpoints", ["checkpoint_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_patrol_round_checkpoints_checkpoint_id"), table_name="patrol_round_checkpoints")
    op.drop_index(op.f("ix_patrol_round_checkpoints_round_id"), table_name="patrol_round_checkpoints")
    op.drop_table("patrol_round_checkpoints")

    op.drop_column("patrol_rounds", "updated_at")
    op.drop_column("patrol_rounds", "created_at")
    op.drop_column("patrol_rounds", "notes")
