# Cuenta experimental de energía y emisiones al aire de Guatemala, 2018–2024

[![Datos: CC BY 4.0](https://img.shields.io/badge/datos-CC%20BY%204.0-1682FC.svg)](LICENSE)
[![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-2EA44F.svg)](LICENSE_CODE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21924042.svg)](https://doi.org/10.5281/zenodo.21924042)
[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala/blob/main/04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb)

Este repositorio presenta una cuenta de flujos físicos de energía y emisiones
al aire para Guatemala, con cobertura anual de 2018 a 2024. La oferta y la
utilización de productos energéticos se organizan en una **tabla física de
oferta y utilización (PSUT)**, los flujos se vinculan con industrias y hogares,
y las emisiones directas se estiman por gas. El marco conceptual es el
**SEEA‑Energy** de Naciones Unidas.

> [!WARNING]
> **Los resultados tienen carácter experimental y no constituyen una
> estadística oficial.**

> [!NOTE]
> Los agregados de emisiones de 2023 y 2024 dependen de aproximaciones
> identificadas como `PRX` (factores de emisión aproximados o, en agricultura,
> prolongación del resultado). El estado de cada registro se conserva en el
> conjunto de datos.

La descripción técnica completa y canónica del paquete se conserva en
[`readme.txt`](readme.txt); esta portada resume el contenido y facilita la
navegación.

## Autores

| Autor | Afiliación | ORCID |
|---|---|---|
| [Juan Alejandro Osorio](https://github.com/JA-Osorio) | Universidad Rafael Landívar | [0009-0001-4260-772X](https://orcid.org/0009-0001-4260-772X) |
| [Patricia Villatoro](https://github.com/patriciavillatoro7) | Universidad Rafael Landívar | [0000-0002-5109-2393](https://orcid.org/0000-0002-5109-2393) |
| [Noe Salguero](https://github.com/noesm7) | Universidad Rafael Landívar | [0009-0004-5017-6538](https://orcid.org/0009-0004-5017-6538) |
| [José Carlos Soberanis](https://github.com/Fxhnd13) | Universidad de San Carlos de Guatemala | [0009-0007-0279-4472](https://orcid.org/0009-0007-0279-4472) |

Los roles CRediT de autoría, colaboración y revisión técnica se documentan en
[`creditos.txt`](creditos.txt).

## Qué contiene

| Componente | Contenido | Acceso directo |
|---|---|---|
| Trazabilidad | Registro estructurado de las fuentes y su procedencia | [`registro_fuentes_psut_guatemala.xlsx`](00_trazabilidad_fuentes/registro_fuentes_psut_guatemala.xlsx) |
| Metodología | Marco general, compilación de la PSUT y cuenta de emisiones | [`01_metodologia/`](01_metodologia/) |
| Resultados y diccionario | CSV finales y definiciones de campos, códigos y estados | [`02_resultados_y_diccionario/`](02_resultados_y_diccionario/) |
| Modelo tabular | Libro de cálculo con fórmulas y trazabilidad | [`modelo_psut_energia_emisiones_guatemala_2018_2024.xlsx`](03_modelo_hoja_calculo/modelo_psut_energia_emisiones_guatemala_2018_2024.xlsx) |
| Reproducción | Insumo derivado, generador, validador y cuaderno visor | [`04_reproduccion_python/`](04_reproduccion_python/) |
| Verificación | Evidencia de la reproducción independiente | [`informe_reproduccion_computacional_guatemala_2018_2024.txt`](05_verificacion/informe_reproduccion_computacional_guatemala_2018_2024.txt) |

Los dos conjuntos finales son:

- [`psut_energia_guatemala_2018_2024.csv`](02_resultados_y_diccionario/psut_energia_guatemala_2018_2024.csv), con 617 registros de oferta y utilización de energía en terajulios;
- [`cuenta_emisiones_aire_guatemala_2018_2024.csv`](02_resultados_y_diccionario/cuenta_emisiones_aire_guatemala_2018_2024.csv), con 374 registros de emisiones y estados de cálculo.

## Resultados principales

Totales anuales cuantificados de emisiones:

| Año | Emisiones (kt CO₂e) | Condición |
|---:|---:|---|
| 2018 | 28 612,88 | Observado/calculado con información del año |
| 2019 | 29 730,98 | Observado/calculado con información del año |
| 2020 | 27 015,69 | Observado/calculado con información del año |
| 2021 | 29 978,96 | Observado/calculado con información del año |
| 2022 | 28 320,98 | Observado/calculado con información del año |
| 2023 | 30 852,29 | 100 % dependiente de aproximaciones `PRX` |
| 2024 | 33 159,61 | 100 % dependiente de aproximaciones `PRX` |

El CO₂ equivalente se calcula de forma uniforme como
`CO₂e = CO₂ fósil + 28 × CH₄ + 265 × N₂O`; el CO₂ biogénico se presenta como
partida informativa y no se suma al CO₂ fósil. La reproducción independiente
aprobó los 47 controles estructurales y numéricos definidos; los detalles
constan en el
[informe de reproducción](05_verificacion/informe_reproduccion_computacional_guatemala_2018_2024.txt).

## Cuaderno visor

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala/blob/main/04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb)

El [cuaderno visor](04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb)
es la forma más sencilla de explorar los resultados: está preparado para
abrirse en **Google Colab** con el botón anterior, sin instalar nada, y
acompaña las cifras con explicaciones que facilitan su lectura. Permite
seleccionar cualquier año entre 2018 y 2024 y presenta una PSUT integrada, una
vista de emisiones, indicadores principales y complementarios, y once gráficas.

El cuaderno consulta los dos CSV finales y **no reemplaza al generador**: no
recalcula las cuentas ni escribe archivos. También puede ejecutarse en un
entorno Jupyter local con las versiones indicadas en
[`requirements.txt`](04_reproduccion_python/requirements.txt), o consultarse
directamente en GitHub.

## Reproducir las cuentas

El generador y el validador utilizan exclusivamente la biblioteca estándar de
Python (se requiere **Python 3.10 o posterior**). Una ejecución conforme
devuelve código de salida `0` y aprueba los 47 controles del validador.

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

## Estructura del repositorio

```text
.
├── 00_trazabilidad_fuentes/      # Registro estructurado de fuentes
├── 01_metodologia/               # Notas metodológicas
├── 02_resultados_y_diccionario/  # CSV finales y diccionario
├── 03_modelo_hoja_calculo/       # Modelo tabular reproducible
├── 04_reproduccion_python/       # Insumo, scripts y cuaderno visor
├── 05_verificacion/              # Informe de reproducción
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

La cuenta mantiene la resolución observada en las fuentes: no crea aperturas
sectoriales mediante ponderadores externos cuando no existe una desagregación
reproducible. Distingue extracción y combustión, atribuye las emisiones de la
electricidad a su generación y preserva como estados diferentes el cero, la
ausencia de dato, lo no estimado y lo incluido en otra categoría.

- [Metodología general](01_metodologia/nt_00_metodologia_general_energia_emisiones_2018_2024.txt)
- [Metodología de la PSUT de energía](01_metodologia/nt_01_metodologia_psut_energia_2018_2024.txt)
- [Metodología de la cuenta de emisiones](01_metodologia/nt_02_metodologia_cuenta_emisiones_aire_2018_2024.txt)
- [Registro de trazabilidad de fuentes](00_trazabilidad_fuentes/registro_fuentes_psut_guatemala.xlsx)

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

**Versión 1.0.0 · Guatemala · cobertura 2018–2024**
