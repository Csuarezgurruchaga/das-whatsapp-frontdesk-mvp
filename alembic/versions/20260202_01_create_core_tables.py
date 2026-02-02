"""create core tables

Revision ID: 20260202_01
Revises: None
Create Date: 2026-02-02

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260202_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("agent", "admin", name="user_role"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "contacts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("whatsapp_number", sa.String(length=64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("contact_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "CHATBOT",
                "EN_ESPERA",
                "ASIGNADO",
                "CERRADO",
                name="conversation_state",
            ),
            nullable=False,
        ),
        sa.Column("assigned_to", sa.BigInteger()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("closed_by", sa.BigInteger()),
        sa.Column("previous_conversation_id", sa.BigInteger()),
        sa.CheckConstraint(
            "(state = 'ASIGNADO' AND assigned_to IS NOT NULL) OR "
            "(state <> 'ASIGNADO' AND assigned_to IS NULL)",
            name="ck_conversations_assigned_to_matches_state",
        ),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["previous_conversation_id"], ["conversations.id"]),
    )

    op.create_index(
        "ix_conversations_state_last_activity",
        "conversations",
        ["state", "last_activity_at"],
    )
    op.create_index(
        "ix_conversations_assigned_last_activity",
        "conversations",
        ["assigned_to", "last_activity_at"],
    )
    op.create_index(
        "ix_conversations_contact_id",
        "conversations",
        ["contact_id"],
    )
    op.create_index(
        "ix_conversations_previous_conversation_id",
        "conversations",
        ["previous_conversation_id"],
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("INBOUND", "OUTBOUND", name="message_direction"),
            nullable=False,
        ),
        sa.Column(
            "sender_type",
            sa.Enum("USER", "BOT", "AGENT", name="message_sender_type"),
            nullable=False,
        ),
        sa.Column("text", sa.Text()),
        sa.Column("whatsapp_message_id", sa.String(length=255)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
    )

    op.create_index(
        "ix_messages_conversation_created_at",
        "messages",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_messages_whatsapp_message_id",
        "messages",
        ["whatsapp_message_id"],
    )

    op.create_table(
        "conversation_read_states",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("last_read_message_id", sa.BigInteger()),
        sa.Column("last_read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["last_read_message_id"], ["messages.id"]),
        sa.UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_read_state_conversation_user",
        ),
    )

    op.create_index(
        "ix_read_state_conversation_id",
        "conversation_read_states",
        ["conversation_id"],
    )
    op.create_index(
        "ix_read_state_user_id",
        "conversation_read_states",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_read_state_user_id", table_name="conversation_read_states")
    op.drop_index("ix_read_state_conversation_id", table_name="conversation_read_states")
    op.drop_table("conversation_read_states")
    op.drop_index("ix_messages_whatsapp_message_id", table_name="messages")
    op.drop_index("ix_messages_conversation_created_at", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_previous_conversation_id", table_name="conversations")
    op.drop_index("ix_conversations_contact_id", table_name="conversations")
    op.drop_index("ix_conversations_assigned_last_activity", table_name="conversations")
    op.drop_index("ix_conversations_state_last_activity", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("contacts")
    op.drop_table("users")
