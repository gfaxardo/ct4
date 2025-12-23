"""fix_jobtype_enum

Revision ID: 006_fix_jobtype_enum
Revises: 005_brand_model_index
Create Date: 2024-01-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_fix_jobtype_enum'
down_revision = '005_brand_model_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Actualizar registros existentes que puedan tener valores NULL o incorrectos
    # Primero, convertir temporalmente a text para poder hacer actualizaciones
    op.execute("""
        ALTER TABLE ops.ingestion_runs 
        ALTER COLUMN job_type TYPE text USING job_type::text
    """)
    
    # Actualizar valores NULL o inválidos
    op.execute("""
        UPDATE ops.ingestion_runs 
        SET job_type = 'identity_run' 
        WHERE job_type IS NULL OR job_type NOT IN ('identity_run', 'drivers_index_refresh')
    """)
    
    # Convertir de vuelta al tipo enum
    op.execute("""
        ALTER TABLE ops.ingestion_runs 
        ALTER COLUMN job_type TYPE jobtype USING job_type::jobtype
    """)


def downgrade() -> None:
    pass

