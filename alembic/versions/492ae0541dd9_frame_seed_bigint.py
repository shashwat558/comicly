"""frame seed bigint

Revision ID: 492ae0541dd9
Revises: 6cbe4ec3ef53
Create Date: 2026-09-10 18:39:40.531852

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '492ae0541dd9'
down_revision: str | None = '6cbe4ec3ef53'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
