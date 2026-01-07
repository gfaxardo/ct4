"""update_drivers_index_upsert

Revision ID: 003_update_drivers_index_upsert
Revises: 002_create_drivers_index
Create Date: 2024-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_update_drivers_index_upsert'
down_revision = '002_create_drivers_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
                hire_date = EXCLUDED.hire_date,
                snapshot_date = EXCLUDED.snapshot_date,
                updated_at = EXCLUDED.updated_at;
            
            GET DIAGNOSTICS rows_affected = ROW_COUNT;
            RETURN rows_affected;
        END;
        $$;
    """)


def downgrade() -> None:
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


































