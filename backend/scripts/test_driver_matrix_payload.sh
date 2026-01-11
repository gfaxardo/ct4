#!/bin/bash
# Script para probar el payload del endpoint driver-matrix
# Verifica que m1_achieved_flag, m5_achieved_flag, m25_achieved_flag estén presentes en el JSON

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "=== Probando GET /api/v1/ops/payments/driver-matrix ==="
echo ""

# Hacer request y guardar en archivo temporal
response=$(curl -s "${API_BASE_URL}/api/v1/ops/payments/driver-matrix?limit=5&offset=0")

# Verificar que la respuesta contiene los campos achieved_flag
if echo "$response" | grep -q "m1_achieved_flag"; then
    echo "✅ m1_achieved_flag está presente en el JSON"
else
    echo "❌ m1_achieved_flag NO está presente en el JSON"
fi

if echo "$response" | grep -q "m5_achieved_flag"; then
    echo "✅ m5_achieved_flag está presente en el JSON"
else
    echo "❌ m5_achieved_flag NO está presente en el JSON"
fi

if echo "$response" | grep -q "m25_achieved_flag"; then
    echo "✅ m25_achieved_flag está presente en el JSON"
else
    echo "❌ m25_achieved_flag NO está presente en el JSON"
fi

echo ""
echo "=== Primer driver del response (muestra campos achieved) ==="
echo "$response" | jq '.data[0] | {driver_id, driver_name, m1_achieved_flag, m1_achieved_date, m5_achieved_flag, m5_achieved_date, m25_achieved_flag, m25_achieved_date}' 2>/dev/null || echo "$response" | head -50



