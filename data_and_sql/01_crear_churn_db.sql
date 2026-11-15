CREATE DATABASE IF NOT EXISTS churn_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE churn_db;

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente VARCHAR(16) PRIMARY KEY,
    genero VARCHAR(16) NOT NULL,
    adulto_mayor TINYINT UNSIGNED NOT NULL CHECK (adulto_mayor IN (0, 1)),
    pareja ENUM('Yes', 'No') NOT NULL,
    dependientes ENUM('Yes', 'No') NOT NULL,
    antiguedad_meses SMALLINT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS servicios (
    id_servicio INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_cliente VARCHAR(16) NOT NULL UNIQUE,
    servicio_telefonico VARCHAR(20) NULL,
    lineas_multiples VARCHAR(20) NULL,
    internet VARCHAR(20) NULL,
    seguridad_en_linea VARCHAR(24) NULL,
    respaldo_en_linea VARCHAR(24) NULL,
    proteccion_dispositivo VARCHAR(24) NULL,
    soporte_tecnico VARCHAR(24) NULL,
    streaming_tv VARCHAR(24) NULL,
    streaming_peliculas VARCHAR(24) NULL,
    CONSTRAINT fk_servicios_cliente FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS facturacion (
    id_cliente VARCHAR(16) PRIMARY KEY,
    tipo_contrato VARCHAR(25) NOT NULL,
    facturacion_digital ENUM('Yes', 'No') NULL,
    metodo_pago VARCHAR(35) NULL,
    cargo_mensual DECIMAL(10, 2) NOT NULL CHECK (cargo_mensual >= 0),
    cargo_total DECIMAL(10, 2) NOT NULL CHECK (cargo_total >= 0),
    INDEX ix_facturacion_contrato (tipo_contrato),
    CONSTRAINT fk_facturacion_cliente FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS registro_churn (
    id_cliente VARCHAR(16) PRIMARY KEY,
    churn ENUM('Yes', 'No') NOT NULL,
    CONSTRAINT fk_churn_cliente FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
) ENGINE=InnoDB;
