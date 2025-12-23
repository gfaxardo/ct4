"""add_brand_model_to_drivers_index

Revision ID: 005_add_brand_model_to_drivers_index
Revises: 004_add_ingestion_run_fields
Create Date: 2024-01-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_brand_model_index'
down_revision = '004_add_ingestion_run_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('drivers_index', sa.Column('brand_norm', sa.String(), nullable=True), schema='canon')
    op.add_column('drivers_index', sa.Column('model_norm', sa.String(), nullable=True), schema='canon')
    
    op.create_index(
        'idx_drivers_index_park_brand_model',
        'drivers_index',
        ['park_id', 'brand_norm', 'model_norm'],
        schema='canon'
    )
    
    op.execute("""
        CREATE OR REPLACE FUNCTION canon.refresh_drivers_index(run_date DATE DEFAULT CURRENT_DATE)
        RETURNS INTEGER
        LANGUAGE plpgsql
        AS $$
        DECLARE
            rows_affected INTEGER;
        BEGIN
            INSERT INTO canon.drivers_index (
                driver_id,
                park_id,
                phone_norm,
                license_norm,
                plate_norm,
                full_name_norm,
                brand_norm,
                model_norm,
                hire_date,
                snapshot_date,
                updated_at
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
                UPPER(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(d.car_brand, ''), '[ÀÁÂÃÄÅ]', 'A', 'g'), '[ÈÉÊË]', 'E', 'g')) AS brand_norm,
                UPPER(REGEXP_REPLACE(REGEXP_REPLACE(COALESCE(d.car_model, ''), '[ÀÁÂÃÄÅ]', 'A', 'g'), '[ÈÉÊË]', 'E', 'g')) AS model_norm,
                d.hire_date,
                run_date AS snapshot_date,
                NOW() AS updated_at
            FROM public.drivers d
            WHERE d.driver_id IS NOT NULL
            ON CONFLICT (driver_id) DO UPDATE SET
                park_id = EXCLUDED.park_id,
                phone_norm = EXCLUDED.phone_norm,
                license_norm = EXCLUDED.license_norm,
                plate_norm = EXCLUDED.plate_norm,
                full_name_norm = EXCLUDED.full_name_norm,
                brand_norm = EXCLUDED.brand_norm,
                model_norm = EXCLUDED.model_norm,
                hire_date = EXCLUDED.hire_date,
                snapshot_date = EXCLUDED.snapshot_date,
                updated_at = EXCLUDED.updated_at;
            
            GET DIAGNOSTICS rows_affected = ROW_COUNT;
            RETURN rows_affected;
        END;
        $$;
    """)


def downgrade() -> None:
    op.execute('DROP FUNCTION IF EXISTS canon.refresh_drivers_index(DATE)')
    op.drop_index('idx_drivers_index_park_brand_model', table_name='drivers_index', schema='canon')
    op.drop_column('drivers_index', 'model_norm', schema='canon')
    op.drop_column('drivers_index', 'brand_norm', schema='canon')

