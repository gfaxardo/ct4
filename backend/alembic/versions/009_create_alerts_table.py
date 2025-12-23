"""create_alerts_table

Revision ID: 009_create_alerts_table
Revises: 008_create_scouting_match_candidates
Create Date: 2025-12-21 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_alerts'
down_revision = '008_scouting_obs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    alert_severity_enum = postgresql.ENUM('info', 'warning', 'error', name='alertseverity', create_type=False)
    alert_severity_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('severity', alert_severity_enum, nullable=False),
        sa.Column('week_label', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['ops.ingestion_runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='ops'
    )
    
    op.create_index(
        'idx_alerts_week_label',
        'alerts',
        ['week_label'],
        schema='ops'
    )
    
    op.create_index(
        'idx_alerts_acknowledged',
        'alerts',
        ['acknowledged_at'],
        schema='ops',
        postgresql_where=sa.text('acknowledged_at IS NULL')
    )


def downgrade() -> None:
    op.drop_index('idx_alerts_acknowledged', table_name='alerts', schema='ops')
    op.drop_index('idx_alerts_week_label', table_name='alerts', schema='ops')
    op.drop_table('alerts', schema='ops')
    op.execute('DROP TYPE IF EXISTS alertseverity')

