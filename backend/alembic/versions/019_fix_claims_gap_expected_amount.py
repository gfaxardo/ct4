"""fix_claims_gap_expected_amount

Revision ID: 019_fix_claims_gap_expected_amount
Revises: 018_claims_cabinet_14d
Create Date: 2024-12-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pathlib import Path

# revision identifiers, used by Alembic.
revision = '019_fix_claims_gap_expected_amount'
down_revision = '018_claims_cabinet_14d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Actualiza ops.v_cabinet_claims_gap_14d para exponer expected_amount
    (alias de amount_expected) para mantener contrato claro con endpoint/UI.
    """
    # Leer el archivo SQL de la vista actualizada
    sql_file = Path(__file__).parent.parent.parent / 'sql' / 'ops' / 'v_cabinet_claims_gap_14d.sql'
    
    if sql_file.exists():
        sql_content = sql_file.read_text(encoding='utf-8')
        # Ejecutar el SQL (CREATE OR REPLACE VIEW)
        op.execute(sql_content)
    else:
        # Fallback: ejecutar solo el cambio necesario
        op.execute("""
            DROP VIEW IF EXISTS ops.v_cabinet_claims_gap_14d CASCADE;
            
            CREATE VIEW ops.v_cabinet_claims_gap_14d AS
            WITH expected_claims AS (
                SELECT 
                    lead_id,
                    lead_source_pk,
                    lead_date_canonico,
                    week_start,
                    person_key,
                    driver_id,
                    window_end_14d,
                    milestone,
                    trips_in_window,
                    milestone_reached,
                    claim_expected,
                    amount_expected,
                    expected_reason_detail
                FROM ops.v_cabinet_claims_expected_14d
            ),
            existing_claims AS (
                SELECT 
                    person_key::uuid AS person_key_uuid,
                    lead_date,
                    milestone,
                    status,
                    generated_at,
                    paid_at
                FROM canon.claims_yango_cabinet_14d
                WHERE status IN ('expected', 'generated', 'paid')
            ),
            claims_gap AS (
                SELECT 
                    ec.lead_id,
                    ec.lead_source_pk,
                    ec.lead_date_canonico,
                    ec.week_start,
                    ec.person_key,
                    ec.driver_id,
                    ec.window_end_14d,
                    ec.milestone,
                    ec.trips_in_window,
                    ec.milestone_reached,
                    ec.claim_expected,
                    ec.amount_expected,
                    ec.expected_reason_detail,
                    (exc.person_key_uuid IS NOT NULL) AS claim_exists,
                    CASE
                        WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 'CLAIM_NOT_GENERATED'
                        WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 'OK'
                        ELSE 'INVALID'
                    END AS claim_status,
                    CASE
                        WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 'CLAIM_NOT_GENERATED'
                        WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 'OK'
                        WHEN ec.expected_reason_detail = 'NO_IDENTITY' THEN 'NO_IDENTITY'
                        WHEN ec.expected_reason_detail = 'NO_DRIVER' THEN 'NO_DRIVER'
                        WHEN ec.expected_reason_detail = 'INSUFFICIENT_TRIPS' THEN 'INSUFFICIENT_TRIPS'
                        ELSE 'OTHER'
                    END AS gap_reason,
                    CASE
                        WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 
                            'Milestone alcanzado pero claim no generado en canon.claims_yango_cabinet_14d'
                        WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 
                            'Claim existe (OK)'
                        WHEN ec.expected_reason_detail = 'NO_IDENTITY' THEN 
                            'Lead no tiene person_key en identity_links'
                        WHEN ec.expected_reason_detail = 'NO_DRIVER' THEN 
                            'Lead tiene person_key pero no tiene driver_id'
                        WHEN ec.expected_reason_detail = 'INSUFFICIENT_TRIPS' THEN 
                            'Trips en ventana 14d (' || ec.trips_in_window || ') < milestone (' || ec.milestone || ')'
                        ELSE 
                            'Razón desconocida: ' || COALESCE(ec.expected_reason_detail, 'NULL')
                    END AS gap_detail
                FROM expected_claims ec
                LEFT JOIN existing_claims exc
                    ON exc.person_key_uuid::text = ec.person_key
                    AND exc.lead_date = ec.lead_date_canonico
                    AND exc.milestone = ec.milestone
            )
            SELECT 
                lead_id,
                lead_source_pk,
                lead_date_canonico AS lead_date,
                week_start,
                person_key,
                driver_id,
                window_end_14d,
                milestone AS milestone_value,
                trips_in_window AS trips_14d,
                milestone_reached AS milestone_achieved,
                claim_expected,
                claim_exists,
                claim_status,
                gap_reason,
                gap_detail,
                amount_expected AS expected_amount
            FROM claims_gap
            WHERE claim_status = 'CLAIM_NOT_GENERATED'
            ORDER BY week_start DESC, lead_date_canonico DESC, milestone DESC;
        """)


def downgrade() -> None:
    """
    Revertir cambio: volver a usar amount_expected sin alias.
    """
    op.execute("""
        DROP VIEW IF EXISTS ops.v_cabinet_claims_gap_14d CASCADE;
        
        CREATE VIEW ops.v_cabinet_claims_gap_14d AS
        WITH expected_claims AS (
            SELECT 
                lead_id,
                lead_source_pk,
                lead_date_canonico,
                week_start,
                person_key,
                driver_id,
                window_end_14d,
                milestone,
                trips_in_window,
                milestone_reached,
                claim_expected,
                amount_expected,
                expected_reason_detail
            FROM ops.v_cabinet_claims_expected_14d
        ),
        existing_claims AS (
            SELECT 
                person_key::uuid AS person_key_uuid,
                lead_date,
                milestone,
                status,
                generated_at,
                paid_at
            FROM canon.claims_yango_cabinet_14d
            WHERE status IN ('expected', 'generated', 'paid')
        ),
        claims_gap AS (
            SELECT 
                ec.lead_id,
                ec.lead_source_pk,
                ec.lead_date_canonico,
                ec.week_start,
                ec.person_key,
                ec.driver_id,
                ec.window_end_14d,
                ec.milestone,
                ec.trips_in_window,
                ec.milestone_reached,
                ec.claim_expected,
                ec.amount_expected,
                ec.expected_reason_detail,
                (exc.person_key_uuid IS NOT NULL) AS claim_exists,
                CASE
                    WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 'CLAIM_NOT_GENERATED'
                    WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 'OK'
                    ELSE 'INVALID'
                END AS claim_status,
                CASE
                    WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 'CLAIM_NOT_GENERATED'
                    WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 'OK'
                    WHEN ec.expected_reason_detail = 'NO_IDENTITY' THEN 'NO_IDENTITY'
                    WHEN ec.expected_reason_detail = 'NO_DRIVER' THEN 'NO_DRIVER'
                    WHEN ec.expected_reason_detail = 'INSUFFICIENT_TRIPS' THEN 'INSUFFICIENT_TRIPS'
                    ELSE 'OTHER'
                END AS gap_reason,
                CASE
                    WHEN ec.claim_expected = true AND exc.person_key_uuid IS NULL THEN 
                        'Milestone alcanzado pero claim no generado en canon.claims_yango_cabinet_14d'
                    WHEN ec.claim_expected = true AND exc.person_key_uuid IS NOT NULL THEN 
                        'Claim existe (OK)'
                    WHEN ec.expected_reason_detail = 'NO_IDENTITY' THEN 
                        'Lead no tiene person_key en identity_links'
                    WHEN ec.expected_reason_detail = 'NO_DRIVER' THEN 
                        'Lead tiene person_key pero no tiene driver_id'
                    WHEN ec.expected_reason_detail = 'INSUFFICIENT_TRIPS' THEN 
                        'Trips en ventana 14d (' || ec.trips_in_window || ') < milestone (' || ec.milestone || ')'
                    ELSE 
                        'Razón desconocida: ' || COALESCE(ec.expected_reason_detail, 'NULL')
                END AS gap_detail
            FROM expected_claims ec
            LEFT JOIN existing_claims exc
                ON exc.person_key_uuid::text = ec.person_key
                AND exc.lead_date = ec.lead_date_canonico
                AND exc.milestone = ec.milestone
        )
        SELECT 
            lead_id,
            lead_source_pk,
            lead_date_canonico AS lead_date,
            week_start,
            person_key,
            driver_id,
            window_end_14d,
            milestone AS milestone_value,
            trips_in_window AS trips_14d,
            milestone_reached AS milestone_achieved,
            claim_expected,
            claim_exists,
            claim_status,
            gap_reason,
            gap_detail,
            amount_expected
        FROM claims_gap
        WHERE claim_status = 'CLAIM_NOT_GENERATED'
        ORDER BY week_start DESC, lead_date_canonico DESC, milestone DESC;
    """)
