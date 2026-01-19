#!/bin/bash

# ============================================================================
# CT4 Identity System - Script de inicio para producción/desarrollo (Ubuntu)
# ============================================================================
# Los procesos quedan corriendo en background:
#   - Backend: uvicorn con nohup (puerto 8001)
#   - Frontend: pm2 (puerto 3001)
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

# Nombres para pm2
PM2_BACKEND_NAME="ct4-backend"
PM2_FRONTEND_NAME="ct4-frontend"

echo -e "${CYAN}"
echo "=============================================="
echo "   CT4 Identity System - Inicio"
echo "=============================================="
echo -e "${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -d "$BASE_DIR/backend" ] || [ ! -d "$BASE_DIR/frontend" ]; then
    echo -e "${RED}Error: No se encontraron los directorios backend/ y frontend/${NC}"
    echo "Ejecuta este script desde la raíz del proyecto CT4"
    exit 1
fi

# Verificar pm2
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}Instalando pm2 globalmente...${NC}"
    sudo npm install -g pm2
fi

# ============================================================================
# BACKEND
# ============================================================================
echo -e "${CYAN}[1/2] Configurando Backend...${NC}"

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

# Detener backend anterior si existe
pm2 delete $PM2_BACKEND_NAME 2>/dev/null || true

# Variables de entorno para el backend
export DATABASE_URL="${DATABASE_URL:-postgresql://ct4_user:ct4_pass@localhost:5432/ct4_db}"
export AUTO_PROCESS_LEADS="${AUTO_PROCESS_LEADS:-true}"
export AUTO_PROCESS_INTERVAL_MINUTES="${AUTO_PROCESS_INTERVAL_MINUTES:-5}"

# Crear script wrapper para pm2
cat > "$BASE_DIR/backend/start-backend.sh" << EOF
#!/bin/bash
cd $BASE_DIR/backend
source venv/bin/activate
export DATABASE_URL="${DATABASE_URL}"
export AUTO_PROCESS_LEADS="${AUTO_PROCESS_LEADS}"
export AUTO_PROCESS_INTERVAL_MINUTES="${AUTO_PROCESS_INTERVAL_MINUTES}"
exec uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT
EOF
chmod +x "$BASE_DIR/backend/start-backend.sh"

# Iniciar backend con pm2
echo -e "${GREEN}Iniciando Backend en puerto $BACKEND_PORT...${NC}"
pm2 start "$BASE_DIR/backend/start-backend.sh" --name $PM2_BACKEND_NAME --cwd "$BASE_DIR/backend"

# ============================================================================
# FRONTEND
# ============================================================================
echo -e "${CYAN}[2/2] Configurando Frontend...${NC}"

cd "$BASE_DIR/frontend"

# Instalar dependencias si es necesario
if [ package.json -nt node_modules/.installed ] 2>/dev/null || [ ! -f node_modules/.installed ]; then
    echo -e "${YELLOW}Instalando dependencias del frontend...${NC}"
    npm install --silent
    touch node_modules/.installed
fi

# Build del frontend (producción)
if [ ! -d ".next" ] || [ "$1" == "--build" ]; then
    echo -e "${YELLOW}Construyendo frontend...${NC}"
    NEXT_PUBLIC_API_BASE_URL="http://localhost:$BACKEND_PORT" npm run build
fi

# Detener frontend anterior si existe
pm2 delete $PM2_FRONTEND_NAME 2>/dev/null || true

# Iniciar frontend con pm2
echo -e "${GREEN}Iniciando Frontend en puerto $FRONTEND_PORT...${NC}"
NEXT_PUBLIC_API_BASE_URL="http://localhost:$BACKEND_PORT" pm2 start npm --name $PM2_FRONTEND_NAME --cwd "$BASE_DIR/frontend" -- start -- -p $FRONTEND_PORT

# Guardar configuración de pm2
pm2 save

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
echo -e "${YELLOW}Comandos útiles:${NC}"
echo "  pm2 status          - Ver estado de los procesos"
echo "  pm2 logs            - Ver logs en tiempo real"
echo "  pm2 logs $PM2_BACKEND_NAME   - Ver logs del backend"
echo "  pm2 logs $PM2_FRONTEND_NAME  - Ver logs del frontend"
echo "  pm2 restart all     - Reiniciar todos los procesos"
echo "  pm2 stop all        - Detener todos los procesos"
echo "  pm2 delete all      - Eliminar todos los procesos"
echo ""

# Mostrar estado
pm2 status
