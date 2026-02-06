"""add attachment metadata table

Revision ID: 20260206_01
Revises: 20260202_03
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260206_01"
down_revision = "20260202_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachment_metadata",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("attachment_id", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_relpath", sa.String(length=1024), nullable=False),
        sa.Column(
            "status",
            sa.Enum("uploading", "sent", "failed", name="attachment_status"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint(
            "attachment_id",
            name="uq_attachment_metadata_attachment_id",
        ),
    )

    op.create_index(
        "ix_attachment_metadata_conversation_id",
        "attachment_metadata",
        ["conversation_id"],
    )
    op.create_index(
        "ix_attachment_metadata_message_id",
        "attachment_metadata",
        ["message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_attachment_metadata_message_id", table_name="attachment_metadata")
    op.drop_index(
        "ix_attachment_metadata_conversation_id",
        table_name="attachment_metadata",
    )
    op.drop_table("attachment_metadata")
