#!/bin/bash

# ============================================================================
# CT4 Identity System - Script de inicio para VPS (Ubuntu)
# ============================================================================
# - Backend: Python con nohup (no pm2)
# - Frontend: pm2 con npm run dev (modo desarrollo)
# ============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directorio base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cargar configuración desde config.sh si existe
if [ -f "$BASE_DIR/config.sh" ]; then
    echo -e "${CYAN}Cargando configuración desde config.sh...${NC}"
    source "$BASE_DIR/config.sh"
else
    echo -e "${YELLOW}ADVERTENCIA: No se encontró config.sh${NC}"
    echo -e "${YELLOW}Copia config.sh.example a config.sh y configura tus credenciales:${NC}"
    echo -e "  cp config.sh.example config.sh"
    echo ""
fi

# Valores por defecto si no están en config.sh
BACKEND_PORT="${BACKEND_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3001}"
PUBLIC_IP="${PUBLIC_IP:-localhost}"
DATABASE_URL="${DATABASE_URL:-postgresql://ct4_user:ct4_pass@localhost:5432/ct4_db}"

echo -e "${CYAN}"
echo "=============================================="
echo "   CT4 Identity System - Inicio"
echo "=============================================="
echo -e "${NC}"

# Verificar directorios
if [ ! -d "$BASE_DIR/backend" ] || [ ! -d "$BASE_DIR/frontend" ]; then
    echo -e "${RED}Error: No se encontraron backend/ y frontend/${NC}"
    exit 1
fi

# Verificar pm2
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}Instalando pm2...${NC}"
    npm install -g pm2
fi

# ============================================================================
# DETENER PROCESOS ANTERIORES
# ============================================================================
echo -e "${YELLOW}Deteniendo procesos anteriores...${NC}"

# Matar backend anterior
pkill -f "uvicorn app.main:app.*$BACKEND_PORT" 2>/dev/null || true

# Matar frontend anterior
pm2 delete ct4-frontend 2>/dev/null || true

sleep 2

# ============================================================================
# BACKEND (Python con nohup)
# ============================================================================
echo -e "${CYAN}[1/2] Iniciando Backend (Python)...${NC}"

cd "$BASE_DIR/backend"

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creando entorno virtual...${NC}"
    python3 -m venv venv
fi

# Instalar dependencias
source venv/bin/activate
if [ requirements.txt -nt venv/.installed ] 2>/dev/null || [ ! -f venv/.installed ]; then
    echo -e "${YELLOW}Instalando dependencias...${NC}"
    pip install -q -r requirements.txt
    touch venv/.installed
fi

# Exportar variables de entorno
export DATABASE_URL="$DATABASE_URL"
export AUTO_PROCESS_LEADS="${AUTO_PROCESS_LEADS:-true}"
export AUTO_PROCESS_INTERVAL_MINUTES="${AUTO_PROCESS_INTERVAL_MINUTES:-5}"

echo -e "  DATABASE_URL: ${DATABASE_URL:0:50}..."

# Crear directorio de logs
mkdir -p "$BASE_DIR/backend/logs"

# Iniciar backend con nohup
echo -e "${GREEN}Iniciando Backend en puerto $BACKEND_PORT...${NC}"
nohup "$BASE_DIR/backend/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port $BACKEND_PORT > "$BASE_DIR/backend/logs/uvicorn.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$BASE_DIR/backend/backend.pid"

# Esperar a que inicie
echo -n "Esperando backend"
for i in {1..15}; do
    if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# ============================================================================
# FRONTEND (pm2 con dev mode)
# ============================================================================
echo -e "${CYAN}[2/2] Iniciando Frontend (Next.js)...${NC}"

cd "$BASE_DIR/frontend"

# Instalar dependencias
if [ ! -d "node_modules" ] || [ package.json -nt node_modules/.installed ]; then
    echo -e "${YELLOW}Instalando dependencias...${NC}"
    npm install
    touch node_modules/.installed
fi

# Iniciar con pm2 en modo desarrollo
echo -e "${GREEN}Iniciando Frontend en puerto $FRONTEND_PORT...${NC}"
NEXT_PUBLIC_API_BASE_URL="http://${PUBLIC_IP}:${BACKEND_PORT}" pm2 start npm --name ct4-frontend -- run dev -- -p $FRONTEND_PORT

pm2 save

# ============================================================================
# RESUMEN
# ============================================================================
echo ""
echo -e "${GREEN}=============================================="
echo "   ✓ CT4 Identity System Iniciado"
echo "=============================================="
echo -e "${NC}"
echo -e "  ${CYAN}Frontend:${NC} http://${PUBLIC_IP}:$FRONTEND_PORT"
echo -e "  ${CYAN}Backend:${NC}  http://${PUBLIC_IP}:$BACKEND_PORT"
echo -e "  ${CYAN}API Docs:${NC} http://${PUBLIC_IP}:$BACKEND_PORT/docs"
echo ""
echo -e "${YELLOW}Comandos útiles:${NC}"
echo "  pm2 logs ct4-frontend     - Logs del frontend"
echo "  tail -f backend/logs/uvicorn.log  - Logs del backend"
echo "  ./stop-dev.sh             - Detener todo"
echo ""
pm2 status
