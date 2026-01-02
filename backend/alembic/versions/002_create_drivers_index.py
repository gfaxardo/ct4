"""create_drivers_index

Revision ID: 002_create_drivers_index
Revises: 001_create_canon_schema
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_create_drivers_index'
down_revision = '001_create_canon_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'drivers_index',
        sa.Column('driver_id', sa.String(), nullable=False),
        sa.Column('park_id', sa.String(), nullable=True),
        sa.Column('phone_norm', sa.String(), nullable=True),
        sa.Column('license_norm', sa.String(), nullable=True),
        sa.Column('plate_norm', sa.String(), nullable=True),
        sa.Column('full_name_norm', sa.String(), nullable=True),
        sa.Column('hire_date', sa.Date(), nullable=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('driver_id'),
        schema='canon'
    )

    op.create_index(
        'idx_drivers_index_park_phone',
        'drivers_index',
        ['park_id', 'phone_norm'],
        schema='canon'
    )

    op.create_index(
        'idx_drivers_index_park_license',
        'drivers_index',
        ['park_id', 'license_norm'],
        schema='canon'
    )

    op.create_index(
        'idx_drivers_index_park_plate',
        'drivers_index',
        ['park_id', 'plate_norm'],
        schema='canon'
    )

    op.create_index(
        'idx_drivers_index_phone',
        'drivers_index',
        ['phone_norm'],
        schema='canon'
    )

    op.create_index(
        'idx_drivers_index_license',
        'drivers_index',
        ['license_norm'],
        schema='canon'
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION canon.refresh_drivers_index(run_date DATE DEFAULT CURRENT_DATE)
        RETURNS INTEGER
        LANGUAGE plpgsql
        AS $$
        DECLARE
            rows_inserted INTEGER;
        BEGIN
            DELETE FROM canon.drivers_index;
            
            INSERT INTO canon.drivers_index (
                driver_id,
                park_id,
                phone_norm,
                license_norm,
                plate_norm,
                full_name_norm,
                hire_date,
                snapshot_date
            )
            SELECT
                d.driver_id,
                d.park_id,
                REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(d.phone, ''), '[\\s\\-()+]', '', 'g'), '^\\+', ''), '[^0-9]', '', 'g'), '^', '') AS phone_norm,
                UPPER(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(COALESCE(d.license_normalized_number, d.license_number), ''), '[\\s\\-]', '', 'g'), '[^A-Z0-9]', '', 'g')) AS license_norm,
                UPPER(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(COALESCE(d.car_normalized_number, d.car_number), ''), '[\\s\\-]', '', 'g'), '[^A-Z0-9]', '', 'g')) AS plate_norm,
                UPPER(REGEXP_REPLACE(REGEXP_REPLACE(
                    COALESCE(d.full_name, 
                        TRIM(COALESCE(d.first_name, '') || ' ' || COALESCE(d.middle_name, '') || ' ' || COALESCE(d.last_name, ''))
                    ), 
                    '[ÀÁÂÃÄÅ]', 'A', 'g'
                ), '[ÈÉÊË]', 'E', 'g')) AS full_name_norm,
                d.hire_date,
                run_date AS snapshot_date
            FROM public.drivers d
            WHERE d.driver_id IS NOT NULL;
            
            GET DIAGNOSTICS rows_inserted = ROW_COUNT;
            RETURN rows_inserted;
        END;
        $$;
    """)


def downgrade() -> None:
    op.execute('DROP FUNCTION IF EXISTS canon.refresh_drivers_index(DATE)')
    op.drop_index('idx_drivers_index_license', table_name='drivers_index', schema='canon')
    op.drop_index('idx_drivers_index_phone', table_name='drivers_index', schema='canon')
    op.drop_index('idx_drivers_index_park_plate', table_name='drivers_index', schema='canon')
    op.drop_index('idx_drivers_index_park_license', table_name='drivers_index', schema='canon')
    op.drop_index('idx_drivers_index_park_phone', table_name='drivers_index', schema='canon')
    op.drop_table('drivers_index', schema='canon')

























