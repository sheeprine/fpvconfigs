"""Initial schema: users, configurations, revisions

Revision ID: 0001
Revises:
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "configurations",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("board_name", sa.String(64), nullable=True),
        sa.Column("manufacturer_id", sa.String(64), nullable=True),
        sa.Column("craft_name", sa.String(255), nullable=True),
        sa.Column("pilot_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_configurations_user_id", "configurations", ["user_id"])

    op.create_table(
        "revisions",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("config_id", sa.String(36), sa.ForeignKey("configurations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("betaflight_version", sa.String(64), nullable=True),
        sa.Column("msp_api_version", sa.String(16), nullable=True),
        sa.Column("config_revision", sa.String(64), nullable=True),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("config_id", "revision_number", name="uq_config_revision_number"),
    )
    op.create_index("ix_revisions_config_id", "revisions", ["config_id"])


def downgrade() -> None:
    op.drop_table("revisions")
    op.drop_table("configurations")
    op.drop_table("users")
