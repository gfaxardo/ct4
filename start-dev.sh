#!/bin/bash

# ============================================================================
# CT4 Identity System - Script de inicio para desarrollo (Ubuntu)
# ============================================================================
# Usa puertos alternativos para no bloquear servicios existentes:
#   - Backend: 8001 (en lugar de 8000)
#   - Frontend: 3001 (en lugar de 3000)
# ============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Puertos (cambiar si es necesario)
BACKEND_PORT=8001
FRONTEND_PORT=3001

# Directorio base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}"
echo "=============================================="
echo "   CT4 Identity System - Inicio Dev"
echo "=============================================="
echo -e "${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -d "$BASE_DIR/backend" ] || [ ! -d "$BASE_DIR/frontend" ]; then
    echo -e "${RED}Error: No se encontraron los directorios backend/ y frontend/${NC}"
    echo "Ejecuta este script desde la raíz del proyecto CT4"
    exit 1
fi

# Función para matar procesos en puertos específicos
cleanup() {
    echo -e "\n${YELLOW}Deteniendo servicios...${NC}"
    
    # Matar procesos por puerto
    if lsof -ti:$BACKEND_PORT > /dev/null 2>&1; then
        kill $(lsof -ti:$BACKEND_PORT) 2>/dev/null || true
    fi
    if lsof -ti:$FRONTEND_PORT > /dev/null 2>&1; then
        kill $(lsof -ti:$FRONTEND_PORT) 2>/dev/null || true
    fi
    
    # Matar jobs de este script
    jobs -p | xargs -r kill 2>/dev/null || true
    
    echo -e "${GREEN}Servicios detenidos${NC}"
    exit 0
}

# Trap para limpiar al salir
trap cleanup SIGINT SIGTERM

# Verificar si los puertos están libres
check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        echo -e "${YELLOW}Advertencia: Puerto $port en uso. Intentando liberar...${NC}"
        kill $(lsof -ti:$port) 2>/dev/null || true
        sleep 1
    fi
}

check_port $BACKEND_PORT
check_port $FRONTEND_PORT

# ============================================================================
# BACKEND
# ============================================================================
echo -e "${CYAN}[1/2] Iniciando Backend en puerto $BACKEND_PORT...${NC}"

cd "$BASE_DIR/backend"

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creando entorno virtual...${NC}"
    python3 -m venv venv
fi

# Activar venv e instalar dependencias
source venv/bin/activate

# Verificar si hay dependencias nuevas
if [ requirements.txt -nt venv/.installed ] 2>/dev/null || [ ! -f venv/.installed ]; then
    echo -e "${YELLOW}Instalando dependencias del backend...${NC}"
    pip install -q -r requirements.txt
    touch venv/.installed
fi

# Variables de entorno para el backend
export DATABASE_URL="${DATABASE_URL:-postgresql://ct4_user:ct4_pass@localhost:5432/ct4_db}"
export AUTO_PROCESS_LEADS="${AUTO_PROCESS_LEADS:-true}"
export AUTO_PROCESS_INTERVAL_MINUTES="${AUTO_PROCESS_INTERVAL_MINUTES:-5}"

# Iniciar backend en background
echo -e "${GREEN}Backend iniciando en http://localhost:$BACKEND_PORT${NC}"
uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!

# Esperar a que el backend esté listo
echo -n "Esperando backend"
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# ============================================================================
# FRONTEND
# ============================================================================
echo -e "${CYAN}[2/2] Iniciando Frontend en puerto $FRONTEND_PORT...${NC}"

cd "$BASE_DIR/frontend"

# Instalar dependencias si es necesario
if [ package.json -nt node_modules/.installed ] 2>/dev/null || [ ! -f node_modules/.installed ]; then
    echo -e "${YELLOW}Instalando dependencias del frontend...${NC}"
    npm install --silent
    touch node_modules/.installed
fi

# Variables de entorno para el frontend
export NEXT_PUBLIC_API_BASE_URL="http://localhost:$BACKEND_PORT"
export PORT=$FRONTEND_PORT

# Iniciar frontend en background
echo -e "${GREEN}Frontend iniciando en http://localhost:$FRONTEND_PORT${NC}"
npm run dev -- -p $FRONTEND_PORT &
FRONTEND_PID=$!

# ============================================================================
# RESUMEN
# ============================================================================
echo ""
echo -e "${GREEN}=============================================="
echo "   ✓ CT4 Identity System Iniciado"
echo "=============================================="
echo -e "${NC}"
echo -e "  ${CYAN}Backend:${NC}  http://localhost:$BACKEND_PORT"
echo -e "  ${CYAN}Frontend:${NC} http://localhost:$FRONTEND_PORT"
echo -e "  ${CYAN}API Docs:${NC} http://localhost:$BACKEND_PORT/docs"
echo ""
echo -e "${YELLOW}Presiona Ctrl+C para detener todos los servicios${NC}"
echo ""

# Mantener el script corriendo
wait
