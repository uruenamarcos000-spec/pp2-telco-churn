"""Genera los tres gráficos de la actividad 5."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from etl import RESULTS, ROOT

MATRIZ = np.array([[280, -50], [-600, 0]])
GRAFICOS = ROOT / "graficos"
CONTRATOS = {"Month-to-month": "Mes a mes", "One year": "Un año", "Two year": "Dos años"}


def guardar(fig, nombre):
    fig.savefig(GRAFICOS / nombre, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generar(datos):
    GRAFICOS.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid")
    tasas = (datos.assign(baja=datos.churn.eq("Yes")).groupby("tipo_contrato")["baja"]
             .mean().mul(100).reindex(CONTRATOS).rename("tasa").reset_index())
    tasas.to_csv(RESULTS / "tasas_contrato.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.1))
    sns.barplot(data=tasas.assign(contrato=tasas.tipo_contrato.map(CONTRATOS)),
                x="contrato", y="tasa", color="#138779", ax=ax)
    for barra in ax.patches:
        altura = barra.get_height()
        ax.annotate(f"{altura:.1f}%", (barra.get_x() + barra.get_width()/2, altura),
                    xytext=(0, 6), textcoords="offset points", ha="center", weight="bold")
    ax.set(xlabel="", ylabel="Clientes que se dieron de baja (%)", ylim=(0, 50))
    guardar(fig, "churn_por_contrato.png")

    fig, ax = plt.subplots(figsize=(8, 4.1))
    sns.kdeplot(data=datos, x="antiguedad_meses", hue="churn", hue_order=["No", "Yes"],
                palette={"No": "#138779", "Yes": "#c74343"}, fill=True, common_norm=False,
                clip=(0, 72), ax=ax)
    plt.axvline(12, linestyle="--", color="#34465d")
    ax.set(xlim=(0, 72), xlabel="Antigüedad (meses)", ylabel="Densidad por grupo")
    ax.legend(handles=ax.get_legend().legend_handles, labels=["Activos", "Bajas"], loc="upper right")
    guardar(fig, "densidad_antiguedad.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    sns.heatmap(MATRIZ, annot=True, fmt="d", cmap="RdYlGn", center=0, linewidths=1,
                xticklabels=["Baja real", "Activo real"], yticklabels=["Contactar", "No contactar"],
                cbar_kws={"label": "USD por cliente"}, ax=ax)
    ax.tick_params(axis="y", labelrotation=0)
    guardar(fig, "matriz_decision_financiera.png")


if __name__ == "__main__":
    generar(pd.read_csv(RESULTS / "clientes_procesados.csv"))
