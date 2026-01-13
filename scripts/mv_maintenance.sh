#!/bin/bash
# ==============================================================================
# MV Maintenance Script - Refresca las vistas materializadas críticas
# ==============================================================================
# 
# Uso:
#   ./mv_maintenance.sh              # Refrescar todas las MVs
#   ./mv_maintenance.sh --priority 1 # Solo prioridad alta
#   ./mv_maintenance.sh --mv NAME    # Solo una MV específica
#
# Para programar en cron (cada hora):
#   0 * * * * /ruta/a/mv_maintenance.sh >> /var/log/mv_maintenance.log 2>&1
#
# ==============================================================================

API_URL="${API_URL:-http://localhost:8000}"
PRIORITY=""
MV_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --priority)
            PRIORITY="$2"
            shift 2
            ;;
        --mv)
            MV_NAME="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "=============================================="
echo "MV Maintenance - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# Build URL
URL="$API_URL/api/v1/ops/mv-maintenance/refresh"
PARAMS=""
if [ -n "$PRIORITY" ]; then
    PARAMS="priority=$PRIORITY"
fi
if [ -n "$MV_NAME" ]; then
    [ -n "$PARAMS" ] && PARAMS="$PARAMS&"
    PARAMS="mv_name=$MV_NAME"
fi
if [ -n "$PARAMS" ]; then
    URL="$URL?$PARAMS"
fi

echo "URL: $URL"
echo ""

# Execute refresh
RESPONSE=$(curl -s -X POST "$URL")

if [ $? -ne 0 ]; then
    echo "ERROR: No se pudo conectar con la API"
    exit 1
fi

# Parse and display results
echo "$RESPONSE" | python3 -c "
import json
import sys

data = json.load(sys.stdin)

if 'summary' in data:
    s = data['summary']
    print(f\"Resumen:\")
    print(f\"  Total MVs:  {s['total']}\")
    print(f\"  Exitosas:   {s['success']}\")
    print(f\"  Errores:    {s['errors']}\")
    print(f\"  Duración:   {s['total_duration_seconds']}s\")
    print()
    
    print(\"Detalles:\")
    for r in data.get('results', []):
        status = '✓' if r['status'] == 'success' else '✗'
        duration = r.get('duration_seconds', 0)
        method = f\"({r.get('method', 'n/a')})\" if r['status'] == 'success' else f\"({r.get('error', 'unknown')[:30]}...)\"
        print(f\"  {status} {r['mv']}: {duration:.1f}s {method}\")
else:
    # Single MV result
    for r in data.get('results', []):
        status = '✓' if r['status'] == 'success' else '✗'
        print(f\"  {status} {r['mv']}: {r.get('duration_seconds', 0):.1f}s\")
"

echo ""
echo "Completado: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
