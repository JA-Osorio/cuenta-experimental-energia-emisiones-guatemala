# Cuadro físico de oferta y utilización de energía y tabla de emisiones al aire de Guatemala, 2018–2024

[![Datos: CC BY 4.0](https://img.shields.io/badge/datos-CC%20BY%204.0-1682FC.svg)](LICENSE)
[![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-2EA44F.svg)](LICENSE_CODE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21924042.svg)](https://doi.org/10.5281/zenodo.21924042)
[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala/blob/main/04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb)
[![Abrir el portal interactivo](https://img.shields.io/badge/Portal_interactivo-ABRIR-168A68.svg)](https://ja-osorio.github.io/cuenta-experimental-energia-emisiones-guatemala/)

Este repositorio reúne los materiales de la investigación sobre la compilación inicial de energía y emisiones al aire de Guatemala, para el período 2018–2024. Incluye los datos, el modelo de cálculo, los programas y la documentación que permiten consultar y reproducir los resultados.

El trabajo desarrolla un **cuadro físico de oferta y utilización de energía (COU-F), vinculado con una tabla de emisiones al aire**. La construcción parte de los balances energéticos nacionales y de la información del inventario de emisiones, conserva las categorías que identifican las fuentes y documenta las correspondencias, los cálculos y las aproximaciones utilizadas.

Esta construcción constituye una primera etapa para desarrollar las cuentas de energía y emisiones al aire. Establece una base reproducible para avanzar en la desagregación por actividad económica, el ajuste al principio de residencia y la incorporación de información adicional.

> [!WARNING]
> **Los resultados tienen carácter experimental y no constituyen una
> estadística oficial.**

> [!NOTE]
> Los agregados de emisiones de 2023 y 2024 dependen de aproximaciones
> identificadas como `PRX` (factores de emisión aproximados o, en agricultura,
> prolongación del resultado). El estado de cada registro se conserva en el
> conjunto de datos.

El archivo [`readme.txt`](readme.txt) describe la cobertura, las fuentes y la
estructura de los datos.

## Portal interactivo

El [portal interactivo](https://ja-osorio.github.io/cuenta-experimental-energia-emisiones-guatemala/)
permite explorar las series de energía y emisiones de 2018 a 2024, consultar
los indicadores económicos y descargar los datos. La aplicación y los datos
económicos complementarios se encuentran en [`docs/`](docs/).

## Qué contiene

| Carpeta | Qué contiene |
|---|---|
| [`00_trazabilidad_fuentes/`](00_trazabilidad_fuentes/) | Registro de las fuentes de información utilizadas para elaborar el cuadro de energía y la tabla de emisiones. |
| [`01_metodologia/`](01_metodologia/) | Metodología y procedimientos de cálculo del cuadro de energía y de la tabla de emisiones al aire. |
| [`02_resultados_y_diccionario/`](02_resultados_y_diccionario/) | Resultados en CSV y diccionario que explica las variables, unidades y códigos. |
| [`03_modelo_hoja_calculo/`](03_modelo_hoja_calculo/) | Modelo del cuadro de energía y de la tabla de emisiones en Excel, con sus fórmulas de cálculo. |
| [`04_reproduccion_python/`](04_reproduccion_python/) | Datos de entrada, programas y cuaderno para reproducir y explorar los resultados en Python. |
| [`05_verificacion/`](05_verificacion/) | Informes y resultados de las comprobaciones de cálculo, factores de emisión y cobertura de las fuentes. |
| [`docs/`](docs/) | Portal interactivo para explorar energía, emisiones e indicadores económicos y descargar los datos. [Abrir portal](https://ja-osorio.github.io/cuenta-experimental-energia-emisiones-guatemala/). |
| [`tests/`](tests/) | Comprobaciones automáticas de la lectura de datos y su incorporación al portal. |

Los dos conjuntos finales son:

- [`psut_energia_guatemala_2018_2024.csv`](02_resultados_y_diccionario/psut_energia_guatemala_2018_2024.csv), con 617 registros de oferta y utilización de energía en terajulios;
- [`cuenta_emisiones_aire_guatemala_2018_2024.csv`](02_resultados_y_diccionario/cuenta_emisiones_aire_guatemala_2018_2024.csv), con 374 registros de emisiones y estados de cálculo.

## Cuaderno visor

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala/blob/main/04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb)

El [cuaderno visor](04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb)
permite seleccionar cualquier año entre 2018 y 2024 y consultar el COU-F, las emisiones y los indicadores. Incluye once gráficas.

Lee los dos CSV finales, sin recalcular los resultados ni escribir archivos.
Puede abrirse en **Google Colab**, ejecutarse en Jupyter con las versiones
indicadas en [`requirements.txt`](04_reproduccion_python/requirements.txt)
o consultarse directamente en GitHub.

## Reproducir los resultados

El generador y el validador utilizan exclusivamente la biblioteca estándar de
Python (se requiere **Python 3.10 o posterior**). Una ejecución conforme
devuelve código de salida `0` y aprueba los 55 controles del validador.

### Linux, macOS o Git Bash

```bash
git clone https://github.com/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala.git
cd cuenta-experimental-energia-emisiones-guatemala
python3 04_reproduccion_python/reproducir_modelo_guatemala_2018_2024.py \
  --entrada 04_reproduccion_python/datos_modelo_guatemala_2018_2024.csv \
  --salida resultados_reproducidos
python3 04_reproduccion_python/validar_reproduccion_guatemala_2018_2024.py \
  --generados resultados_reproducidos \
  --referencias 02_resultados_y_diccionario
```

### Windows (CMD)

```bat
git clone https://github.com/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala.git
cd cuenta-experimental-energia-emisiones-guatemala
py -3 04_reproduccion_python\reproducir_modelo_guatemala_2018_2024.py ^
  --entrada 04_reproduccion_python\datos_modelo_guatemala_2018_2024.csv ^
  --salida resultados_reproducidos
py -3 04_reproduccion_python\validar_reproduccion_guatemala_2018_2024.py ^
  --generados resultados_reproducidos ^
  --referencias 02_resultados_y_diccionario
```

Las instrucciones ampliadas, las tolerancias y el alcance exacto de la prueba
están en
[`instrucciones_reproduccion_python.txt`](04_reproduccion_python/instrucciones_reproduccion_python.txt)
y en el
[informe de reproducción](05_verificacion/informe_reproduccion_computacional_guatemala_2018_2024.txt).

Las trece pruebas de regresión comprueban el tratamiento de gases sin factor,
la asignación por producto y la propagación de fuentes y estados:

```bash
python3 -m unittest discover -s 04_reproduccion_python -p "test_*.py" -v
```

## Estructura del repositorio

```text
.
├── 00_trazabilidad_fuentes/      # Registro estructurado de fuentes
├── 01_metodologia/               # Notas metodológicas
├── 02_resultados_y_diccionario/  # CSV finales y diccionario
├── 03_modelo_hoja_calculo/       # Modelo tabular reproducible
├── 04_reproduccion_python/       # Insumo, scripts y cuaderno visor
├── 05_verificacion/              # Informes, factores de emisión y controles
├── docs/                         # Portal de energía, emisiones e indicadores
├── tests/                        # Comprobaciones de lectura de datos del portal
├── CITATION.cff                  # Metadatos de citación
├── LICENSE                       # Datos y documentación: CC BY 4.0
├── LICENSE_CODE                  # Código: MIT
├── manifiesto_archivos.txt       # Inventario y huellas SHA-256
└── readme.txt                    # Descripción técnica canónica
```

El [`manifiesto_archivos.txt`](manifiesto_archivos.txt) documenta el tamaño y
la huella SHA‑256 de cada archivo del paquete de publicación. Los documentos y
datos de fuente primaria no se redistribuyen.

## Metodología y alcance

La compilación mantiene la resolución observada en las fuentes: no crea aperturas
sectoriales mediante ponderadores externos cuando no existe una desagregación
reproducible. Distingue extracción y combustión, atribuye las emisiones de la
electricidad a su generación y preserva como estados diferentes el cero, la
ausencia de dato, lo no estimado y lo incluido en otra categoría.

- [Metodología general](01_metodologia/nt_00_metodologia_general_energia_emisiones_2018_2024.txt)
- [Metodología del cuadro físico de oferta y utilización de energía](01_metodologia/nt_01_metodologia_psut_energia_2018_2024.txt)
- [Metodología de la tabla de emisiones](01_metodologia/nt_02_metodologia_cuenta_emisiones_aire_2018_2024.txt)
- [Registro de trazabilidad de fuentes](00_trazabilidad_fuentes/registro_fuentes_psut_guatemala.xlsx)

Los factores se consultan en la hoja `DATOS_MODELO` del Excel o en el
[CSV de entrada](04_reproduccion_python/datos_modelo_guatemala_2018_2024.csv),
filtrando `tipo_registro = FACTOR_EMISION_OBS`. La hoja `EMISIONES_LARGA`
muestra el factor aplicado a cada registro. La combustión utiliza factores
por combustible y uso. En transporte, gasolina, diésel y GLP emplean factores
anuales específicos de las CRT; la gasolina integra la gasolina de motor y
de aviación. Para las demás combinaciones se utilizan parámetros por
combustible y uso documentados en el BTR1 y las Directrices IPCC 2006,
identificados como `PRX`. La fuente y el estado se conservan por gas.

El insumo contiene 555 factores: 391 positivos, 90 ceros metodológicos y 74
sin valor numérico. El [cotejo con las CRT originales](05_verificacion/revision_factores_crt_2018_2022.txt)
verifica los 106 factores positivos procedentes de esas tablas. Los otros 285
parámetros positivos están documentados en el insumo y la
[metodología de emisiones](01_metodologia/nt_02_metodologia_cuenta_emisiones_aire_2018_2024.txt).

## Citación

Use la opción **Cite this repository** de GitHub o consulte
[`CITATION.cff`](CITATION.cff). La atribución sugerida es:

> Osorio, Juan Alejandro; Villatoro, Patricia; Salguero, Noe; y Soberanis,
> José Carlos. *Cuenta experimental de energía y emisiones al aire de
> Guatemala, 2018–2024*, v1.0.0. Zenodo.
> <https://doi.org/10.5281/zenodo.21924043>. CC BY 4.0.

El DOI [`10.5281/zenodo.21924043`](https://doi.org/10.5281/zenodo.21924043)
identifica la versión 1.0.0; el DOI conceptual
[`10.5281/zenodo.21924042`](https://doi.org/10.5281/zenodo.21924042) dirige
siempre a la versión más reciente.

## Licencias

| Material | Licencia |
|---|---|
| Datos derivados, documentación, tablas, figuras y contenido del cuaderno | [CC BY 4.0](LICENSE) |
| Código Python y celdas ejecutables originales del cuaderno | [MIT](LICENSE_CODE) |

Los materiales de terceros y las fuentes primarias conservan sus derechos y
condiciones de uso de origen; este producto no los relicencia.

---

**Guatemala · cobertura 2018–2024**
