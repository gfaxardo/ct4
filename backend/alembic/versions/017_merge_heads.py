"""merge_heads

Revision ID: 017_merge_heads
Revises: 014_driver_orphan_quarantine, 016_cabinet_kpi_red_recovery_queue
Create Date: 2025-01-22 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '017_merge_heads'
down_revision = ('014_driver_orphan_quarantine', '016_kpi_red_recovery_queue')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration: no changes needed, just unifying the branches
    # Both 014_driver_orphan_quarantine and 016_cabinet_kpi_red_recovery_queue
    # are already applied (or will be applied before this merge)
    pass


def downgrade() -> None:
    # Merge migration: no changes needed
    pass
