# Sistema predictivo de retención de clientes
**Práctica Profesionalizante II · Técnico Superior en Ciencia de Datos e Inteligencia Artificial**

El proyecto estima el riesgo de baja en una base histórica de una empresa de telecomunicaciones. Una matriz de costos y beneficios permite decidir a qué clientes contactar según el valor financiero simulado.

## Ejecución

**En Google Colab.** Abrir `notebooks/PP2_Colab.ipynb` desde Colab con **Archivo → Subir notebook**. Ejecutar la primera celda y, cuando se solicite, subir `Proyecto_PP2.zip`. Ejecutar el resto de las celdas en orden.

**En VS Code o terminal.** Extraer el ZIP, abrir la carpeta `PP2` con un intérprete Python 3.11 o 3.12 y ejecutar:

```bash
python -m pip install -r requirements.txt
python notebooks/etl.py
python notebooks/visualizar.py
python notebooks/modelar.py
python notebooks/explorar.py
```

El CSV adjunto proviene del repositorio [IBM Telco Customer Churn](https://github.com/IBM/telco-customer-churn-on-icp4d). El ETL lo vuelve a descargar si falta. `notebooks/generar_dataset_pp2.py` conserva el script provisto por la cátedra.

**En MySQL 8 / Workbench.** Ejecutar `data_and_sql/01_crear_churn_db.sql` en el servidor. Desde la terminal, configurar `CHURN_DB_URL` con la cadena SQLAlchemy de la base y ejecutar `python notebooks/etl.py --mysql`. Ejemplo en PowerShell:

```powershell
$env:CHURN_DB_URL = "mysql+pymysql://usuario:clave@127.0.0.1:3306/churn_db"
python notebooks/etl.py --mysql
```

Codificar los caracteres especiales de usuario/contraseña en la URL y mantener las credenciales fuera del repositorio. En Workbench, abrir `consultas_churn.sql` y `clase4_dml_transacciones.sql` y ejecutar cada bloque en orden en una conexión de práctica. Si Safe Updates rechaza la actualización masiva intencional, desactivarlo solo en esa sesión de práctica con `SET SQL_SAFE_UPDATES = 0;` y restaurarlo al terminar con `SET SQL_SAFE_UPDATES = 1;`.

## Actividades resueltas

| Clase | Archivos | Evidencia |
|---|---|---|
| 1 | `notebooks/generar_dataset_pp2.py`, `data_and_sql/Telco_Customer_Churn.csv` | Hipótesis inicial: mayor riesgo en contratos mes a mes y al principio de la relación. |
| 2 | `notebooks/PP2_Colab.ipynb`, `notebooks/etl.py`, `data_and_sql/DER_churn.pdf`, `01_crear_churn_db.sql` | Auditoría, limpieza, imputación, DER y carga ETL transaccional. |
| 3 | `data_and_sql/consultas_churn.sql` | Consultas con alias, filtros, LIKE, ORDER BY y LIMIT. La consulta final valida la brecha de churn por contrato. |
| 4 | `data_and_sql/clase4_dml_transacciones.sql` | Alta de prueba, simulación de aumento, eliminación filtrada y restauración. |
| 5 | `notebooks/visualizar.py`, `graficos/`, `resultados/tablero.html` | Tres gráficos de la consigna y tablero interactivo. |
| 6 | `Informe_Tecnico_PP2.pdf`, `Defensa_PP2.pptx` | Informe y defensa de siete diapositivas con notas para ocho minutos. |

## Arquitectura y normalización

Cada fila del dataset representa una fotografía por cliente. `clientes` contiene los atributos personales y la antigüedad. `servicios`, `facturacion` y `registro_churn` separan los atributos de cada dominio. Cada cliente tiene como máximo una fila hija en cada tabla. En servicios, `id_servicio` es PK autoincremental e `id_cliente` es FK y clave candidata UNIQUE. Las otras dos tablas hijas usan `id_cliente` como PK y FK. Las columnas son atómicas y, para las dependencias declaradas de esta fotografía, cada atributo depende de una clave candidata completa. Se conservan juntos el resumen de facturación y el contrato porque en este dataset el tipo de contrato admite distintos cargos y medios de pago. El gasto histórico acumulado es un dato observado que no se deduce del precio mensual actual. La separación evita volver a almacenar los atributos del cliente al consultar cada dominio. Las categorías de servicio como «No internet service» conservan la distinción original de la fuente.

La FK bloquea filas hijas huérfanas. El alta relacionada usa COMMIT para persistir el conjunto. Las simulaciones de aumento del 10 % y purga filtrada usan ROLLBACK para recuperar el estado previo.

## Diccionario de datos

| Tabla | Campos | Significado |
|---|---|---|
| clientes | id_cliente, genero, adulto_mayor, pareja, dependientes, antiguedad_meses | Identificador, atributos demográficos y meses de relación. adulto_mayor es un indicador 0/1. |
| servicios | id_servicio, id_cliente, servicio_telefonico, lineas_multiples, internet | Identificador técnico, vínculo al cliente y servicios básicos. |
| servicios | seguridad_en_linea, respaldo_en_linea, proteccion_dispositivo, soporte_tecnico, streaming_tv, streaming_peliculas | Servicios adicionales. Los valores de origen distinguen Sí, No y servicio base ausente. |
| facturacion | id_cliente, tipo_contrato, facturacion_digital, metodo_pago, cargo_mensual, cargo_total | Modalidad contractual, preferencias de facturación y cobro, importes mensual y acumulado. |
| registro_churn | id_cliente, churn | Etiqueta observada. Yes indica baja y No indica continuidad. |

Se imputaron 11 cargos acumulados con cero USD porque todos correspondían a antigüedad cero. Se conservaron 7.043 clientes. El chequeo IQR no marcó valores atípicos en los tres campos numéricos analizados. Se excluyó el identificador del entrenamiento y se creó el cargo acumulado por mes. El CSV no contiene fechas de transacción ni compras recurrentes para calcular un RFM clásico. El balanceo por submuestreo se aplica dentro de cada fold, preservando la prevalencia original en validación y prueba.

## Hallazgos visuales y análisis financiero

![Churn por contrato](graficos/churn_por_contrato.png)

Los contratos mes a mes registran 42,7 % de bajas, frente a 11,3 % en contratos anuales y 2,8 % en contratos a dos años. Es una asociación descriptiva que puede orientar un piloto de migración.

![Densidad de antigüedad](graficos/densidad_antiguedad.png)

Las bajas se concentran en los primeros meses. Entre 0 y 12 meses, se dieron de baja 1.037 de 2.186 clientes (47,4 %). La mediana de antigüedad es de 10 meses en bajas y 38 en activos. Las curvas muestran la densidad interna de cada grupo.

![Matriz financiera](graficos/matriz_decision_financiera.png)

| Decisión | Baja real | Cliente activo |
|---|---:|---:|
| Contactar | +280 USD (VP) | −50 USD (FP) |
| No contactar | −600 USD (FN) | 0 USD (VN) |

En el mapa de calor, el falso negativo representa una baja real que el programa deja sin contactar. La matriz le asigna una pérdida de 600 USD por cliente, frente a un costo de 50 USD por contactar a un cliente que iba a seguir activo. Esta diferencia de costos explica por qué la política evalúa cortes bajos.

Con riesgo de baja p, el valor esperado de contactar es 280p − 50(1−p) y el de no contactar es −600p. La diferencia es 930p − 50. El punto de equilibrio teórico es 50/930 = 5,38 %, bajo los supuestos de la matriz. La búsqueda empírica en validación seleccionó Random Forest al 5 %. En 1.409 clientes de prueba, obtuvo AUC ROC 0,842, precisión de contacto 35,0 %, sensibilidad 98,1 % y valor simulado +64.410 USD. La política de contactar a todos obtuvo +52.970 USD. La comparación completa está en `resultados/comparacion_modelos.csv`.

El ROI simulado frente a no actuar es 550,1 %, con costo supuesto de 50 USD por contacto y beneficio bruto incremental de 930 USD por baja real contactada. Para medir retorno efectivo se necesita un piloto con grupo de control y tasa de aceptación observada.

## Entrega en GitHub

Crear un repositorio público llamado `pp2-telco-churn` y subir el **contenido** de esta carpeta, manteniendo `README.md` en la raíz. En la interfaz web elegir **Add file → Upload files → Commit changes**. Comprobar que los gráficos se muestran y que no se incluyen credenciales ni archivos de configuración local.

## Verificación de la entrega

Los scripts de Python se ejecutaron de principio a fin sobre el CSV incluido. El DDL, las consultas y los ejercicios DML se ejecutaron en MariaDB 11.8 con los 7.043 registros, como comprobación de compatibilidad SQL. El alta de prueba persistió con 85,50 USD, el ajuste lo llevó a 94,05 USD dentro de la transacción y el ROLLBACK lo restauró a 85,50 USD. Se eliminaron dos registros de baja dentro de la transacción de prueba y ambos se restauraron. La conexión de SQLAlchemy a MySQL Workbench y la ejecución en la interfaz de Colab requieren los entornos del estudiante.
