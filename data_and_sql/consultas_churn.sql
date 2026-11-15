USE churn_db;

-- 1. Proyección y alias.
SELECT c.id_cliente AS cliente_id,
       c.genero AS genero_cliente,
       c.adulto_mayor AS indicador_adulto_mayor
FROM clientes AS c;

-- 2. Clientes cuyo cargo mensual supera 70.
SELECT f.id_cliente, f.tipo_contrato, f.cargo_mensual
FROM facturacion AS f
WHERE f.cargo_mensual > 70.00;

-- 3a. Contrato mensual y cargo superior a 50.
SELECT f.id_cliente, f.tipo_contrato, f.cargo_mensual, f.metodo_pago
FROM facturacion AS f
WHERE f.tipo_contrato = 'Month-to-month' AND f.cargo_mensual > 50.00;

-- 3b. Agrega a quienes pagan con cheque electrónico.
SELECT f.id_cliente, f.tipo_contrato, f.cargo_mensual, f.metodo_pago
FROM facturacion AS f
WHERE (f.tipo_contrato = 'Month-to-month' AND f.cargo_mensual > 50.00)
   OR f.metodo_pago = 'Electronic check';

-- 4. Busca «Electronic» en cualquier posición y ordena por cargo.
SELECT f.id_cliente, f.metodo_pago, f.cargo_mensual
FROM facturacion AS f
WHERE f.metodo_pago LIKE '%Electronic%'
ORDER BY f.cargo_mensual DESC, f.id_cliente;

-- 5. Top 5 de cargo acumulado.
SELECT f.id_cliente, f.cargo_total
FROM facturacion AS f
ORDER BY f.cargo_total DESC, f.id_cliente
LIMIT 5;

-- Validación del gráfico principal, una vez cargado el CSV.
SELECT f.tipo_contrato, COUNT(*) AS clientes,
       ROUND(100 * AVG(CASE WHEN r.churn = 'Yes' THEN 1 ELSE 0 END), 1) AS tasa_baja_pct
FROM facturacion AS f
JOIN registro_churn AS r ON r.id_cliente = f.id_cliente
GROUP BY f.tipo_contrato
ORDER BY tasa_baja_pct DESC;
