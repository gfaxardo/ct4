#!/bin/bash

# ============================================================================
# CT4 Identity System - Detener servicios
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Deteniendo servicios CT4...${NC}"

pm2 delete ct4-backend 2>/dev/null || true
pm2 delete ct4-frontend 2>/dev/null || true

pm2 save

echo -e "${GREEN}✓ Servicios detenidos${NC}"
pm2 status
