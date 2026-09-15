"""hybrid pipeline: sheets, style bible, frame quality/drift/panels

Revision ID: c41f7a2e9b10
Revises: be7ecd4ea112
Create Date: 2026-09-15

Adds casting sheets + style bible storage and per-frame quality metrics:
- characters.sheet_image_url/key/version
- books.style_bible, books.pro_calls_used
- frames.quality/drift_score/critic_out/panel_layout/retry_count/flagged
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c41f7a2e9b10"
down_revision: str | None = "be7ecd4ea112"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("sheet_image_url", sa.String(length=2000), nullable=True))
    op.add_column("characters", sa.Column("sheet_image_key", sa.String(length=1000), nullable=True))
    op.add_column("characters", sa.Column("sheet_version", sa.Integer(), server_default="0", nullable=False))

    op.add_column("books", sa.Column("style_bible", postgresql.JSONB(), nullable=True))
    op.add_column("books", sa.Column("pro_calls_used", sa.Integer(), server_default="0", nullable=False))

    op.add_column("frames", sa.Column("quality", sa.String(length=16), server_default="auto", nullable=False))
    op.add_column("frames", sa.Column("drift_score", sa.Float(), nullable=True))
    op.add_column("frames", sa.Column("critic_out", postgresql.JSONB(), nullable=True))
    op.add_column("frames", sa.Column("panel_layout", postgresql.JSONB(), nullable=True))
    op.add_column("frames", sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("frames", sa.Column("flagged", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column("frames", "flagged")
    op.drop_column("frames", "retry_count")
    op.drop_column("frames", "panel_layout")
    op.drop_column("frames", "critic_out")
    op.drop_column("frames", "drift_score")
    op.drop_column("frames", "quality")
    op.drop_column("books", "pro_calls_used")
    op.drop_column("books", "style_bible")
    op.drop_column("characters", "sheet_version")
    op.drop_column("characters", "sheet_image_key")
    op.drop_column("characters", "sheet_image_url")
