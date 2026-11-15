"""Compara clasificadores y elige una política con validación independiente."""
import json

import numpy as np
import pandas as pd
from imblearn.pipeline import Pipeline
from imblearn.under_sampling import RandomUnderSampler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from etl import RESULTS
from visualizar import MATRIZ

SEMILLA = 42


def impacto(real, decision):
    tn, fp, fn, tp = confusion_matrix(real, decision, labels=[0, 1]).ravel()
    valor = np.sum(MATRIZ * np.array([[tp, fp], [fn, tn]]))
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp), "valor_usd": int(valor),
            "valor_por_cliente": float(valor / len(real)), "contactos": int(tp + fp)}


def modelar(datos):
    objetivo = datos.churn.eq("Yes").astype(int)
    entradas = datos.drop(columns=["churn", "id_cliente"]).copy()
    # El cargo por mes transcurrido resume facturación histórica disponible.
    entradas["cargo_acumulado_por_mes"] = entradas.cargo_total / entradas.antiguedad_meses.clip(lower=1)
    desarrollo, test = train_test_split(entradas.index, test_size=.20, stratify=objetivo,
                                         random_state=SEMILLA)
    train, valid = train_test_split(desarrollo, test_size=.25, stratify=objetivo.loc[desarrollo],
                                     random_state=SEMILLA)
    categoricas = entradas.select_dtypes(exclude="number").columns.tolist()
    numericas = entradas.select_dtypes(include="number").columns.tolist()
    preprocesador = ColumnTransformer([
        ("categorias", OneHotEncoder(handle_unknown="ignore"), categoricas),
        ("numericas", StandardScaler(), numericas),
    ])
    cv = StratifiedKFold(3, shuffle=True, random_state=SEMILLA)
    modelos = {
        "Regresión logística": (LogisticRegression(max_iter=600), {"modelo__C": [.1, 1, 10]}),
        "Random Forest": (RandomForestClassifier(n_estimators=120, random_state=SEMILLA, n_jobs=1),
                          {"modelo__max_depth": [5, 9, None], "modelo__min_samples_leaf": [2, 10]}),
        "XGBoost": (XGBClassifier(n_estimators=120, learning_rate=.06, random_state=SEMILLA, n_jobs=1),
                    {"modelo__max_depth": [2, 4, 6]}),
    }
    tabla, candidatos = [], []
    for nombre, (algoritmo, grilla) in modelos.items():
        # El submuestreo ocurre dentro de cada fold. La calibración usa folds con prevalencia natural.
        flujo = Pipeline([("prep", preprocesador), ("balanceo", RandomUnderSampler(random_state=SEMILLA)),
                          ("modelo", algoritmo)])
        busqueda = GridSearchCV(flujo, grilla, scoring="roc_auc", cv=cv, n_jobs=1)
        busqueda.fit(entradas.loc[train], objetivo.loc[train])
        calibrado = CalibratedClassifierCV(busqueda.best_estimator_, method="sigmoid", cv=cv)
        calibrado.fit(entradas.loc[train], objetivo.loc[train])
        p_val = calibrado.predict_proba(entradas.loc[valid])[:, 1]
        p_test = calibrado.predict_proba(entradas.loc[test])[:, 1]
        y_val, y_test = objetivo.loc[valid], objetivo.loc[test]
        umbral = max(np.linspace(0, 1, 101),
                     key=lambda t: (impacto(y_val, p_val >= t)["valor_usd"], t))
        val = impacto(y_val, p_val >= umbral)
        fila = {"modelo": nombre, "auc_cv": busqueda.best_score_,
                "auc_validacion": roc_auc_score(y_val, p_val),
                "auc_pr_test": average_precision_score(y_test, p_test),
                "auc_roc_test": roc_auc_score(y_test, p_test), "umbral": float(umbral),
                "valor_validacion_usd": val["valor_usd"],
                "exactitud_test": accuracy_score(y_test, p_test >= umbral),
                "precision_test": precision_score(y_test, p_test >= umbral, zero_division=0),
                "recall_test": recall_score(y_test, p_test >= umbral),
                **impacto(y_test, p_test >= umbral)}
        tabla.append(fila)
        candidatos.append((fila, p_test))

    ganador, probabilidades = max(candidatos, key=lambda par: (
        par[0]["valor_validacion_usd"], par[0]["auc_validacion"]))
    y_test = objetivo.loc[test]
    politica = probabilidades >= ganador["umbral"]
    delta = {nombre: impacto(y_test, decision) for nombre, decision in {
        "ninguno": np.zeros(len(test), dtype=bool), "todos": np.ones(len(test), dtype=bool),
        "umbral_050": probabilidades >= .5, "optimizada": politica,
    }.items()}
    # Para estimar ROI incremental, se aplica un costo de contacto de 50 a ambos grupos. Frente a no actuar, evitar una baja
    # aporta 930 brutos: 600 de pérdida evitada y 330 de margen recuperado.
    costo = 50 * ganador["contactos"]
    recuperado = 930 * ganador["tp"]
    roi = (recuperado - costo) / costo if costo else None
    pd.DataFrame(tabla).to_csv(RESULTS / "comparacion_modelos.csv", index=False)
    pd.DataFrame({"id_cliente": datos.loc[test, "id_cliente"], "baja_real": y_test,
                  "probabilidad_baja": probabilidades, "contactar": politica.astype(int)
                  }).sort_values("probabilidad_baja", ascending=False).to_csv(
                      RESULTS / "predicciones_prueba.csv", index=False)
    resultado = {"ganador": ganador, "politicas": delta,
                 "particiones": {"entrenamiento": len(train), "validacion": len(valid), "prueba": len(test)},
                 "roi_incremental_escenario": roi, "costo_campania_usd": costo,
                 "beneficio_bruto_incremental_usd": recuperado}
    (RESULTS / "modelo.json").write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    print(pd.DataFrame(tabla).to_string(index=False))
    return resultado


if __name__ == "__main__":
    modelar(pd.read_csv(RESULTS / "clientes_procesados.csv"))
