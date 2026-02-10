"""add conversation deletion events table

Revision ID: 20260206_02
Revises: 20260206_01
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260206_02"
down_revision = "20260206_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_deletion_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )

    op.create_index(
        "ix_conversation_deletion_events_conversation_id",
        "conversation_deletion_events",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_deletion_events_created_at",
        "conversation_deletion_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_deletion_events_created_at",
        table_name="conversation_deletion_events",
    )
    op.drop_index(
        "ix_conversation_deletion_events_conversation_id",
        table_name="conversation_deletion_events",
    )
    op.drop_table("conversation_deletion_events")
