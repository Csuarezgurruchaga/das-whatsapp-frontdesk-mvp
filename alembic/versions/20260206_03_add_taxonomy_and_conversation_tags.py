"""add taxonomy tags and conversation tag assignments

Revision ID: 20260206_03
Revises: 20260206_02
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260206_03"
down_revision = "20260206_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'supervisor'")

    op.create_table(
        "taxonomy_tags",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("name", name="uq_taxonomy_tags_name"),
    )
    op.create_index(
        "ix_taxonomy_tags_is_archived",
        "taxonomy_tags",
        ["is_archived"],
    )

    op.create_table(
        "conversation_tags",
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["taxonomy_tags.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("conversation_id", "tag_id"),
    )
    op.create_index(
        "ix_conversation_tags_conversation_id",
        "conversation_tags",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_tags_tag_id",
        "conversation_tags",
        ["tag_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_tags_tag_id", table_name="conversation_tags")
    op.drop_index("ix_conversation_tags_conversation_id", table_name="conversation_tags")
    op.drop_table("conversation_tags")

    op.drop_index("ix_taxonomy_tags_is_archived", table_name="taxonomy_tags")
    op.drop_table("taxonomy_tags")
