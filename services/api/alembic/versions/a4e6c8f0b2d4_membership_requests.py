"""membership_requests

Additive migration for the admin-reviewed request-access workflow: prospective
members submit a request, an admin (nawa:iam:manage) approves or rejects it,
and approval creates a real `User` row via the existing signup/password-reset
path.

Revision ID: a4e6c8f0b2d4
Revises: b7f2c1a9d4e3
Create Date: 2026-07-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4e6c8f0b2d4"
down_revision: Union[str, Sequence[str], None] = "b7f2c1a9d4e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "membership_requests",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("organization", sa.String(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected')", name="ck_membership_requests_status"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_membership_requests_reviewed_by_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_membership_requests"),
    )
    op.create_index(
        "ix_membership_requests_status_created",
        "membership_requests",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_membership_requests_status_created", table_name="membership_requests")
    op.drop_table("membership_requests")
