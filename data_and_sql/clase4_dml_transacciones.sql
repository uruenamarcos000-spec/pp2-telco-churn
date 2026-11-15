USE churn_db;

-- 1. Alta del cliente de práctica. Los datos de servicios y pago quedaron sin especificar.
START TRANSACTION;
INSERT INTO clientes (id_cliente, genero, adulto_mayor, pareja, dependientes)
VALUES ('9999-NEWCL', 'Female', 0, 'Yes', 'No')
ON DUPLICATE KEY UPDATE id_cliente = '9999-NEWCL';

INSERT INTO servicios (id_cliente)
VALUES ('9999-NEWCL')
ON DUPLICATE KEY UPDATE id_cliente = '9999-NEWCL';

INSERT INTO facturacion (id_cliente, tipo_contrato, cargo_mensual, cargo_total)
VALUES ('9999-NEWCL', 'Month-to-month', 85.50, 85.50)
ON DUPLICATE KEY UPDATE cargo_mensual = 85.50, cargo_total = 85.50;
COMMIT;
SELECT id_cliente, tipo_contrato, cargo_mensual, cargo_total
FROM facturacion WHERE id_cliente = '9999-NEWCL';

-- 2. Reajuste de prueba. WHERE usa el índice de contrato.
START TRANSACTION;
SELECT id_cliente, cargo_mensual AS antes
FROM facturacion WHERE tipo_contrato = 'Month-to-month'
ORDER BY id_cliente LIMIT 5;

UPDATE facturacion
SET cargo_mensual = ROUND(cargo_mensual * 1.10, 2)
WHERE tipo_contrato = 'Month-to-month';

SELECT id_cliente, cargo_mensual AS simulado
FROM facturacion WHERE tipo_contrato = 'Month-to-month'
ORDER BY id_cliente LIMIT 5;
ROLLBACK;

SELECT id_cliente, cargo_mensual AS restaurado
FROM facturacion WHERE tipo_contrato = 'Month-to-month'
ORDER BY id_cliente LIMIT 5;

-- 3. Usa IDs reales de dos bajas del CSV. Revisa y confirma con ROLLBACK de práctica.
START TRANSACTION;
SELECT id_cliente, churn FROM registro_churn
WHERE id_cliente IN ('3668-QPYBK', '9237-HQITU') AND churn = 'Yes'
ORDER BY id_cliente FOR UPDATE;

DELETE FROM registro_churn
WHERE id_cliente IN ('3668-QPYBK', '9237-HQITU') AND churn = 'Yes';
SELECT ROW_COUNT() AS registros_borrados;
SELECT id_cliente, churn FROM registro_churn
WHERE id_cliente IN ('3668-QPYBK', '9237-HQITU');
ROLLBACK;
