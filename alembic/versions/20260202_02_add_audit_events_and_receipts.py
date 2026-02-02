"""add audit events and message receipts

Revision ID: 20260202_02
Revises: 20260202_01
Create Date: 2026-02-02

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260202_02"
down_revision = "20260202_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "TAKEN",
                "REASSIGNED",
                "CLOSED",
                "MESSAGE_SENT_FAILED",
                "LOGIN_SUCCESS",
                "LOGIN_FAIL",
                name="conversation_event_type",
            ),
            nullable=False,
        ),
        sa.Column("actor_user_id", sa.BigInteger()),
        sa.Column("meta_json", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )

    op.create_index(
        "ix_conversation_events_conversation_id",
        "conversation_events",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_events_created_at",
        "conversation_events",
        ["created_at"],
    )

    op.create_table(
        "message_receipts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("message_id", sa.BigInteger()),
        sa.Column("whatsapp_message_id", sa.String(length=255)),
        sa.Column(
            "status",
            sa.Enum(
                "sent",
                "delivered",
                "read",
                "failed",
                name="message_receipt_status",
            ),
            nullable=False,
        ),
        sa.Column("payload_raw", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "message_id IS NOT NULL OR whatsapp_message_id IS NOT NULL",
            name="ck_message_receipts_message_or_whatsapp_id",
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
    )

    op.create_index(
        "ix_message_receipts_message_id",
        "message_receipts",
        ["message_id"],
    )
    op.create_index(
        "ix_message_receipts_whatsapp_message_id",
        "message_receipts",
        ["whatsapp_message_id"],
    )
    op.create_index(
        "ix_message_receipts_created_at",
        "message_receipts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_message_receipts_created_at", table_name="message_receipts")
    op.drop_index("ix_message_receipts_whatsapp_message_id", table_name="message_receipts")
    op.drop_index("ix_message_receipts_message_id", table_name="message_receipts")
    op.drop_table("message_receipts")
    op.drop_index("ix_conversation_events_created_at", table_name="conversation_events")
    op.drop_index(
        "ix_conversation_events_conversation_id",
        table_name="conversation_events",
    )
    op.drop_table("conversation_events")
