#!/bin/bash

# ============================================================================
# CT4 Identity System - Detener servicios
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}Deteniendo servicios CT4...${NC}"

# Detener frontend (pm2)
pm2 delete ct4-frontend 2>/dev/null || true

# Detener backend (Python)
if [ -f "$BASE_DIR/backend/backend.pid" ]; then
    PID=$(cat "$BASE_DIR/backend/backend.pid")
    kill $PID 2>/dev/null || true
    rm "$BASE_DIR/backend/backend.pid"
    echo -e "${GREEN}Backend detenido (PID: $PID)${NC}"
fi

# Matar cualquier proceso uvicorn restante en el puerto
pkill -f "uvicorn app.main:app.*8001" 2>/dev/null || true

pm2 save 2>/dev/null || true

echo -e "${GREEN}✓ Todos los servicios detenidos${NC}"
