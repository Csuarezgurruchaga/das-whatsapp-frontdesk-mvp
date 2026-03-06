"""expand user_role enum to include supervisor on supported dialects

Revision ID: 20260305_01
Revises: 20260206_03
Create Date: 2026-03-05

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_01"
down_revision = "20260206_03"
branch_labels = None
depends_on = None


_OLD_USER_ROLE = sa.Enum("agent", "admin", name="user_role")
_NEW_USER_ROLE = sa.Enum("agent", "admin", "supervisor", name="user_role")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'supervisor'")
        return

    if bind.dialect.name == "mysql":
        op.alter_column(
            "users",
            "role",
            existing_type=_OLD_USER_ROLE,
            type_=_NEW_USER_ROLE,
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        supervisor_count = bind.execute(
            sa.text("SELECT COUNT(*) FROM users WHERE role = 'supervisor'")
        ).scalar_one()
        if supervisor_count:
            raise RuntimeError(
                "Cannot downgrade user_role enum while supervisor users exist"
            )
        op.alter_column(
            "users",
            "role",
            existing_type=_NEW_USER_ROLE,
            type_=_OLD_USER_ROLE,
            existing_nullable=False,
        )
