"""add indexes on foreign key columns for query performance

Revision ID: c7e3a1f50d91
Revises: b48aaf102a6c
Create Date: 2026-03-22 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c7e3a1f50d91'
down_revision: Union[str, Sequence[str], None] = 'b48aaf102a6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes on foreign key columns for chapters and content_blocks."""
    op.create_index("ix_chapters_project_id", "chapters", ["project_id"])
    op.create_index("ix_content_blocks_chapter_id", "content_blocks", ["chapter_id"])
    op.create_index(
        "ix_content_blocks_chapter_status",
        "content_blocks",
        ["chapter_id", "status"],
    )


def downgrade() -> None:
    """Remove foreign key indexes."""
    op.drop_index("ix_content_blocks_chapter_status", table_name="content_blocks")
    op.drop_index("ix_content_blocks_chapter_id", table_name="content_blocks")
    op.drop_index("ix_chapters_project_id", table_name="chapters")
