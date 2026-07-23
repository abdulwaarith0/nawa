"""pii_token_maps

Additive migration for the pseudonymizer's persisted mapping
(05-ai-infrastructure.md §5.2). The mapping is Postgres-only.

Revision ID: b7f2c1a9d4e3
Revises: ef80b9a4412b
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f2c1a9d4e3"
down_revision: Union[str, Sequence[str], None] = "ef80b9a4412b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pii_token_maps",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column(
            "tokens",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name="pk_pii_token_maps"),
        sa.UniqueConstraint("subject_type", "subject_id", name="uq_pii_token_maps_subject"),
    )


def downgrade() -> None:
    op.drop_table("pii_token_maps")
