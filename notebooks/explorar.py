"""EDA complementario: correlaciones, segmentos y tablero interactivo local."""
import json

import pandas as pd
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from etl import RESULTS

METRICAS = ["antiguedad_meses", "cargo_mensual", "cargo_total"]


def analizar(datos):
    base = datos.assign(
        baja=datos.churn.eq("Yes").astype(int),
        etapa=datos.antiguedad_meses.le(12).map({True: "0 a 12 meses", False: "Más de 12 meses"}),
    )
    base[METRICAS + ["baja"]].corr().to_csv(RESULTS / "correlaciones.csv")
    cubo = (base.groupby(["tipo_contrato", "etapa", "metodo_pago"])["baja"]
            .agg(clientes="size", bajas="sum").reset_index())
    cubo.to_csv(RESULTS / "cruce_contrato_antiguedad_pago.csv", index=False)

    # K-means descriptivo. Se excluye Churn del ajuste y se usa al perfilar cada grupo.
    x = StandardScaler().fit_transform(base[METRICAS])
    base["grupo"] = KMeans(n_clusters=3, random_state=42, n_init=20).fit_predict(x)
    perfil = base.groupby("grupo").agg(clientes=("baja", "size"), tasa_baja=("baja", "mean"),
                                      mediana_meses=("antiguedad_meses", "median"),
                                      cargo_mensual_medio=("cargo_mensual", "mean"))
    perfil.to_csv(RESULTS / "perfiles_kmeans.csv")

    resumen = (base.groupby(["tipo_contrato", "etapa"], as_index=False)
               .agg(clientes=("baja", "size"), bajas=("baja", "sum")))
    resumen["tasa_pct"] = 100 * resumen.bajas / resumen.clientes
    contratos = px.bar(resumen, x="tipo_contrato", y="tasa_pct", color="etapa", barmode="group",
                       hover_data=["clientes", "bajas"], labels={"tasa_pct": "Bajas (%)",
                       "tipo_contrato": "Contrato", "etapa": "Antigüedad"},
                       title="Tasa de baja por contrato y antigüedad")
    modelo = json.loads((RESULTS / "modelo.json").read_text())
    politicas = pd.DataFrame(list(modelo["politicas"].values()))
    politicas["politica"] = ["Sin campaña", "Contactar a todos", "Umbral 50 %", "Umbral validado"]
    costos = px.bar(politicas, x="politica", y="valor_usd", hover_data=["contactos", "fn", "fp"],
                    labels={"valor_usd": "Valor simulado (USD)", "politica": "Política"},
                    title="Resultado financiero según política · muestra de prueba")
    html = ("<!doctype html><html lang='es'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Telco Churn | Tablero</title><body style='max-width:1100px;margin:40px auto;"
            "padding:0 20px;font-family:system-ui;color:#14263d'><h1>Retención de clientes Telco</h1>"
            "<p>Los gráficos permiten inspeccionar los segmentos y comparar cuatro políticas simuladas.</p>"
            + contratos.to_html(full_html=False, include_plotlyjs=True)
            + costos.to_html(full_html=False, include_plotlyjs=False) + "</body></html>")
    (RESULTS / "tablero.html").write_text(html, encoding="utf-8")
    return perfil


if __name__ == "__main__":
    print(analizar(pd.read_csv(RESULTS / "clientes_procesados.csv")))
