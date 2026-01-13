-- Vista KPI: Drivers con actividad sin identidad
-- Mide drivers que aparecen en summary_daily pero NO tienen identity_link
-- Grano: 1 fila por date_file
-- 
-- Esta vista es INDEPENDIENTE de los leads. Mide un problema diferente:
-- drivers que tienen actividad operativa pero nunca fueron linkeados a person_key.

CREATE OR REPLACE VIEW ops.v_identity_driver_unlinked_activity AS
SELECT 
    sd.date_file,
    COUNT(DISTINCT sd.driver_id) FILTER (
        WHERE NOT EXISTS (
            SELECT 1
            FROM canon.identity_links il
            WHERE il.source_table = 'drivers'
              AND il.source_pk = sd.driver_id
        )
    ) AS drivers_without_identity_count,
    SUM(sd.count_orders_completed) FILTER (
        WHERE NOT EXISTS (
            SELECT 1
            FROM canon.identity_links il
            WHERE il.source_table = 'drivers'
              AND il.source_pk = sd.driver_id
        )
    ) AS trips_from_unlinked_drivers
FROM public.summary_daily sd
WHERE sd.date_file IS NOT NULL
GROUP BY sd.date_file
ORDER BY sd.date_file DESC;

COMMENT ON VIEW ops.v_identity_driver_unlinked_activity IS 
'KPI: Drivers con actividad sin identidad. Mide drivers en summary_daily que NO tienen identity_link. Grano: 1 fila por date_file.';

COMMENT ON COLUMN ops.v_identity_driver_unlinked_activity.date_file IS 
'Fecha del archivo (date_file de summary_daily)';

COMMENT ON COLUMN ops.v_identity_driver_unlinked_activity.drivers_without_identity_count IS 
'Número de drivers únicos sin identity_link que tienen actividad en esta fecha';

COMMENT ON COLUMN ops.v_identity_driver_unlinked_activity.trips_from_unlinked_drivers IS 
'Total de viajes completados por drivers sin identity_link en esta fecha';
