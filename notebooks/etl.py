"""Exploración, limpieza y carga a MySQL del dataset de la cátedra."""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_and_sql"
RESULTS = ROOT / "resultados"
URL = "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv"
COLUMNS = {
    "customerID": "id_cliente", "gender": "genero", "SeniorCitizen": "adulto_mayor",
    "Partner": "pareja", "Dependents": "dependientes", "tenure": "antiguedad_meses",
    "PhoneService": "servicio_telefonico", "MultipleLines": "lineas_multiples",
    "InternetService": "internet", "OnlineSecurity": "seguridad_en_linea",
    "OnlineBackup": "respaldo_en_linea", "DeviceProtection": "proteccion_dispositivo",
    "TechSupport": "soporte_tecnico", "StreamingTV": "streaming_tv",
    "StreamingMovies": "streaming_peliculas", "Contract": "tipo_contrato",
    "PaperlessBilling": "facturacion_digital", "PaymentMethod": "metodo_pago",
    "MonthlyCharges": "cargo_mensual", "TotalCharges": "cargo_total", "Churn": "churn",
}
TABLES = {
    "clientes": ["id_cliente", "genero", "adulto_mayor", "pareja", "dependientes", "antiguedad_meses"],
    "servicios": ["id_cliente", "servicio_telefonico", "lineas_multiples", "internet",
                  "seguridad_en_linea", "respaldo_en_linea", "proteccion_dispositivo",
                  "soporte_tecnico", "streaming_tv", "streaming_peliculas"],
    "facturacion": ["id_cliente", "tipo_contrato", "facturacion_digital", "metodo_pago",
                    "cargo_mensual", "cargo_total"],
    "registro_churn": ["id_cliente", "churn"],
}


def extraer():
    """Usa la lógica del script inicial de la cátedra y conserva una copia local."""
    archivo = DATA / "Telco_Customer_Churn.csv"
    if not archivo.exists():
        pd.read_csv(URL).to_csv(archivo, index=False)
    return pd.read_csv(archivo)


def limpiar(crudo):
    """Rellena el cargo acumulado vacío únicamente cuando la antigüedad es cero."""
    datos = crudo.rename(columns=COLUMNS)[list(COLUMNS.values())].copy()
    textos = datos.select_dtypes(include=["object", "string"]).columns
    datos[textos] = datos[textos].apply(lambda columna: columna.str.strip())
    cargo_ausente = datos["cargo_total"].isna() | datos["cargo_total"].eq("")
    datos["cargo_total"] = pd.to_numeric(datos["cargo_total"].mask(cargo_ausente), errors="raise")
    imputar = cargo_ausente & datos["antiguedad_meses"].eq(0)
    datos.loc[imputar, "cargo_total"] = 0.0
    repetidos = int(datos.duplicated().sum())
    datos = datos.drop_duplicates().reset_index(drop=True)
    if datos["id_cliente"].duplicated().any() or datos["id_cliente"].eq("").any():
        raise ValueError("El identificador debe ser único y no vacío.")
    numericos = ["antiguedad_meses", "cargo_mensual", "cargo_total"]
    if datos.isna().any().any() or not np.isfinite(datos[numericos]).all().all():
        raise ValueError("Hay nulos inesperados o importes no finitos.")
    if not datos["churn"].isin(["Yes", "No"]).all() or datos[numericos].lt(0).any().any():
        raise ValueError("Hay etiquetas o valores fuera de rango.")
    auditoria = pd.DataFrame({
        "campo_original": crudo.columns, "tipo_original": crudo.dtypes.astype(str).values,
        "nulos_originales": crudo.isna().sum().values,
        "blancos_originales": [int(crudo[col].astype(str).str.strip().eq("").sum()) for col in crudo],
        "campo_limpio": datos.columns, "tipo_limpio": datos.dtypes.astype(str).values,
        "nulos_limpios": datos.isna().sum().values,
    })
    q1 = datos[numericos].quantile(.25)
    q3 = datos[numericos].quantile(.75)
    iqr = q3 - q1
    atipicos = (datos[numericos].lt(q1 - 1.5 * iqr) | datos[numericos].gt(q3 + 1.5 * iqr)).sum()
    info = {"filas_origen": len(crudo), "columnas": crudo.shape[1], "filas_finales": len(datos),
            "imputados": int(imputar.sum()), "duplicados_exactos": repetidos,
            "atipicos_iqr": {clave: int(valor) for clave, valor in atipicos.items()}}
    return datos, auditoria, info


def cargar_mysql(datos):
    """Carga atómica de las cuatro tablas mediante upsert, reejecutable."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.dialects.mysql import insert

    motor = create_engine(os.environ["CHURN_DB_URL"])

    def upsert(tabla, conexion, claves, filas):
        sentencia = insert(tabla.table).values([dict(zip(claves, fila)) for fila in filas])
        campos = {clave: sentencia.inserted[clave] for clave in claves if clave != "id_cliente"}
        return conexion.execute(sentencia.on_duplicate_key_update(**campos)).rowcount

    try:
        with motor.begin() as conexion:
            # Comprueba que el DDL ya exista antes de iniciar cualquier carga.
            for tabla in TABLES:
                conexion.execute(text(f"SELECT id_cliente FROM {tabla} LIMIT 1"))
            for tabla, columnas in TABLES.items():
                datos[columnas].to_sql(tabla, conexion, if_exists="append", index=False,
                                       chunksize=300, method=upsert)
    finally:
        motor.dispose()


def ejecutar(mysql=False):
    import json

    crudo = extraer()
    datos, auditoria, info = limpiar(crudo)
    RESULTS.mkdir(exist_ok=True)
    auditoria.to_csv(RESULTS / "auditoria_etl.csv", index=False)
    datos.to_csv(RESULTS / "clientes_procesados.csv", index=False)
    (RESULTS / "etl.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    if mysql:
        cargar_mysql(datos)
    print(info)
    return datos


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--mysql", action="store_true", help="Carga MySQL con CHURN_DB_URL.")
    ejecutar(cli.parse_args().mysql)
