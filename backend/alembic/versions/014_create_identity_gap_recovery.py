"""create_identity_gap_recovery

Revision ID: 014_identity_gap_recovery
Revises: 013_identity_origin
Create Date: 2025-01-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014_identity_gap_recovery'
down_revision = '013_identity_origin'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla ops.identity_matching_jobs
    op.execute("""
        CREATE TABLE IF NOT EXISTS ops.identity_matching_jobs (
            id BIGSERIAL PRIMARY KEY,
            source_type TEXT NOT NULL CHECK (source_type = 'cabinet'),
            source_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'matched', 'failed')),
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_attempt_at TIMESTAMPTZ,
            matched_person_key UUID,
            fail_reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_identity_matching_jobs_person_key 
                FOREIGN KEY (matched_person_key) 
                REFERENCES canon.identity_registry(person_key) 
                ON DELETE SET NULL,
            CONSTRAINT uq_identity_matching_jobs_source 
                UNIQUE (source_type, source_id)
        )
    """)
    
    # Crear índices
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_matching_jobs_status_attempt 
        ON ops.identity_matching_jobs(status, last_attempt_at)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_matching_jobs_source 
        ON ops.identity_matching_jobs(source_type, source_id)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_matching_jobs_person_key 
        ON ops.identity_matching_jobs(matched_person_key)
        WHERE matched_person_key IS NOT NULL
    """)
    
    # Crear función para trigger de history (append-only)
    op.execute("""
        CREATE OR REPLACE FUNCTION canon.identity_origin_history_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                INSERT INTO canon.identity_origin_history (
                    person_key,
                    origin_tag_old,
                    origin_tag_new,
                    origin_source_id_old,
                    origin_source_id_new,
                    origin_confidence_old,
                    origin_confidence_new,
                    resolution_status_old,
                    resolution_status_new,
                    ruleset_version_old,
                    ruleset_version_new,
                    changed_by,
                    change_reason
                ) VALUES (
                    NEW.person_key,
                    OLD.origin_tag::TEXT,
                    NEW.origin_tag::TEXT,
                    OLD.origin_source_id,
                    NEW.origin_source_id,
                    OLD.origin_confidence,
                    NEW.origin_confidence,
                    OLD.resolution_status::TEXT,
                    NEW.resolution_status::TEXT,
                    OLD.ruleset_version,
                    NEW.ruleset_version,
                    COALESCE(NEW.decided_by::TEXT, 'system'),
                    'Auto-updated by system'
                );
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Crear trigger si no existe
    op.execute("""
        DROP TRIGGER IF EXISTS trg_identity_origin_history ON canon.identity_origin;
        CREATE TRIGGER trg_identity_origin_history
        AFTER UPDATE ON canon.identity_origin
        FOR EACH ROW
        WHEN (
            OLD.origin_tag IS DISTINCT FROM NEW.origin_tag OR
            OLD.origin_source_id IS DISTINCT FROM NEW.origin_source_id OR
            OLD.origin_confidence IS DISTINCT FROM NEW.origin_confidence OR
            OLD.resolution_status IS DISTINCT FROM NEW.resolution_status OR
            OLD.ruleset_version IS DISTINCT FROM NEW.ruleset_version
        )
        EXECUTE FUNCTION canon.identity_origin_history_trigger();
    """)
    
    # Revocar permisos de DELETE en identity_origin (solo permitir UPDATE)
    op.execute("""
        REVOKE DELETE ON canon.identity_origin FROM PUBLIC;
    """)
    
    # Agregar comentarios
    op.execute("""
        COMMENT ON TABLE ops.identity_matching_jobs IS 
        'Jobs de reintento de matching para leads sin identidad. Idempotente: puede ejecutarse múltiples veces sin romper.';
        
        COMMENT ON COLUMN ops.identity_matching_jobs.source_type IS 
        'Tipo de fuente: actualmente solo ''cabinet''';
        
        COMMENT ON COLUMN ops.identity_matching_jobs.source_id IS 
        'ID del lead (external_id o id de module_ct_cabinet_leads)';
        
        COMMENT ON COLUMN ops.identity_matching_jobs.status IS 
        'Estado: pending (pendiente de matching), matched (matcheado exitosamente), failed (falló después de N intentos)';
        
        COMMENT ON COLUMN ops.identity_matching_jobs.attempt_count IS 
        'Número de intentos de matching realizados';
        
        COMMENT ON COLUMN ops.identity_matching_jobs.matched_person_key IS 
        'Person key asignado si el matching fue exitoso';
        
        COMMENT ON COLUMN ops.identity_matching_jobs.fail_reason IS 
        'Razón del fallo si status = failed';
    """)


def downgrade() -> None:
    # Eliminar trigger
    op.execute("DROP TRIGGER IF EXISTS trg_identity_origin_history ON canon.identity_origin")
    
    # Eliminar función
    op.execute("DROP FUNCTION IF EXISTS canon.identity_origin_history_trigger()")
    
    # Eliminar índices
    op.execute("DROP INDEX IF EXISTS ops.idx_identity_matching_jobs_person_key")
    op.execute("DROP INDEX IF EXISTS ops.idx_identity_matching_jobs_source")
    op.execute("DROP INDEX IF EXISTS ops.idx_identity_matching_jobs_status_attempt")
    
    # Eliminar tabla
    op.execute("DROP TABLE IF EXISTS ops.identity_matching_jobs")
