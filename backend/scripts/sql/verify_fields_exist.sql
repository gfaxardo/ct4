-- Verificación rápida: campos driver_name e iso_week existen
SELECT 
    column_name, 
    data_type,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'ops'
AND table_name = 'v_cabinet_financial_14d'
AND column_name IN ('driver_id', 'driver_name', 'lead_date', 'iso_week')
ORDER BY ordinal_position;




