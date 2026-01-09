"""create_identity_origin_tables

Revision ID: 013_create_identity_origin
Revises: 012_add_identity_cabinet_payments
Create Date: 2025-01-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_identity_origin'
down_revision = '012_identity_cabinet'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear ENUMs necesarios (solo si no existen)
    # Verificar existencia antes de crear para evitar errores en re-ejecución
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'origin_tag') THEN
                CREATE TYPE origin_tag AS ENUM ('cabinet_lead', 'scout_registration', 'migration', 'legacy_external');
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'decided_by_type') THEN
                CREATE TYPE decided_by_type AS ENUM ('system', 'manual');
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'origin_resolution_status') THEN
                CREATE TYPE origin_resolution_status AS ENUM (
                    'pending_review', 
                    'resolved_auto', 
                    'resolved_manual', 
                    'marked_legacy', 
                    'discarded'
                );
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'violation_reason_type') THEN
                CREATE TYPE violation_reason_type AS ENUM (
                    'missing_origin',
                    'multiple_origins',
                    'late_origin_link',
                    'orphan_lead',
                    'legacy_driver_unclassified'
                );
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recommended_action_type') THEN
                CREATE TYPE recommended_action_type AS ENUM (
                    'auto_link',
                    'manual_review',
                    'mark_legacy',
                    'discard'
                );
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_type_enum') THEN
                CREATE TYPE alert_type_enum AS ENUM (
                    'missing_origin',
                    'multiple_origins',
                    'legacy_unclassified',
                    'orphan_lead'
                );
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_severity_enum') THEN
                CREATE TYPE alert_severity_enum AS ENUM ('low', 'medium', 'high');
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_impact_enum') THEN
                CREATE TYPE alert_impact_enum AS ENUM ('export', 'collection', 'reporting', 'none');
            END IF;
        END $$;
    """)
    
    # Crear tabla canon.identity_origin usando ENUMs existentes
    # Usar text() para evitar que SQLAlchemy intente crear los ENUMs automáticamente
    op.execute("""
        CREATE TABLE IF NOT EXISTS canon.identity_origin (
            person_key UUID NOT NULL PRIMARY KEY,
            origin_tag origin_tag NOT NULL,
            origin_source_id VARCHAR NOT NULL,
            origin_confidence NUMERIC(5,2) NOT NULL,
            origin_created_at TIMESTAMPTZ NOT NULL,
            ruleset_version VARCHAR NOT NULL DEFAULT 'origin_rules_v1',
            evidence JSONB,
            decided_by decided_by_type NOT NULL DEFAULT 'system',
            decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolution_status origin_resolution_status NOT NULL DEFAULT 'pending_review',
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_identity_origin_person_key 
                FOREIGN KEY (person_key) 
                REFERENCES canon.identity_registry(person_key) 
                ON DELETE CASCADE
        )
    """)
    
    # Crear índices solo si no existen
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_tag 
        ON canon.identity_origin(origin_tag)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_status 
        ON canon.identity_origin(resolution_status)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_source_id 
        ON canon.identity_origin(origin_source_id)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_ruleset_version 
        ON canon.identity_origin(ruleset_version)
    """)
    
    # Crear tabla canon.identity_origin_history (append-only)
    op.execute("""
        CREATE TABLE IF NOT EXISTS canon.identity_origin_history (
            id SERIAL PRIMARY KEY,
            person_key UUID NOT NULL,
            origin_tag_old VARCHAR,
            origin_tag_new VARCHAR,
            origin_source_id_old VARCHAR,
            origin_source_id_new VARCHAR,
            origin_confidence_old NUMERIC(5,2),
            origin_confidence_new NUMERIC(5,2),
            resolution_status_old VARCHAR,
            resolution_status_new VARCHAR,
            ruleset_version_old VARCHAR,
            ruleset_version_new VARCHAR,
            changed_by VARCHAR NOT NULL,
            change_reason TEXT,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_identity_origin_history_person_key 
                FOREIGN KEY (person_key) 
                REFERENCES canon.identity_registry(person_key) 
                ON DELETE CASCADE
        )
    """)
    
    # Crear índices solo si no existen
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_history_person_key 
        ON canon.identity_origin_history(person_key)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_history_changed_at 
        ON canon.identity_origin_history(changed_at)
    """)
    
    # Crear tabla ops.identity_origin_alert_state usando SQL directo
    op.execute("""
        CREATE TABLE IF NOT EXISTS ops.identity_origin_alert_state (
            person_key UUID NOT NULL,
            alert_type alert_type_enum NOT NULL,
            first_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMPTZ,
            resolved_by VARCHAR,
            muted_until TIMESTAMPTZ,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT pk_identity_origin_alert_state 
                PRIMARY KEY (person_key, alert_type),
            CONSTRAINT fk_identity_origin_alert_state_person_key 
                FOREIGN KEY (person_key) 
                REFERENCES canon.identity_registry(person_key) 
                ON DELETE CASCADE
        )
    """)
    
    # Crear índices solo si no existen
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_alert_state_resolved 
        ON ops.identity_origin_alert_state(resolved_at)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity_origin_alert_state_muted 
        ON ops.identity_origin_alert_state(muted_until)
    """)


def downgrade() -> None:
    op.drop_index('idx_identity_origin_alert_state_muted', table_name='identity_origin_alert_state', schema='ops')
    op.drop_index('idx_identity_origin_alert_state_resolved', table_name='identity_origin_alert_state', schema='ops')
    op.drop_table('identity_origin_alert_state', schema='ops')
    
    op.drop_index('idx_identity_origin_history_changed_at', table_name='identity_origin_history', schema='canon')
    op.drop_index('idx_identity_origin_history_person_key', table_name='identity_origin_history', schema='canon')
    op.drop_table('identity_origin_history', schema='canon')
    
    op.drop_index('idx_identity_origin_ruleset_version', table_name='identity_origin', schema='canon')
    op.drop_index('idx_identity_origin_source_id', table_name='identity_origin', schema='canon')
    op.drop_index('idx_identity_origin_status', table_name='identity_origin', schema='canon')
    op.drop_index('idx_identity_origin_tag', table_name='identity_origin', schema='canon')
    op.drop_table('identity_origin', schema='canon')
    
    # Eliminar ENUMs
    op.execute('DROP TYPE IF EXISTS alert_impact_enum')
    op.execute('DROP TYPE IF EXISTS alert_severity_enum')
    op.execute('DROP TYPE IF EXISTS alert_type_enum')
    op.execute('DROP TYPE IF EXISTS recommended_action_type')
    op.execute('DROP TYPE IF EXISTS violation_reason_type')
    op.execute('DROP TYPE IF EXISTS origin_resolution_status')
    op.execute('DROP TYPE IF EXISTS decided_by_type')
    op.execute('DROP TYPE IF EXISTS origin_tag')

