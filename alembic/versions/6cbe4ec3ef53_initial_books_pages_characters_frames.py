"""initial books pages characters frames

Revision ID: 6cbe4ec3ef53
Revises: 
Create Date: 2026-09-10 18:32:20.760909

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6cbe4ec3ef53'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
