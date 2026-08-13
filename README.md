# Cuenta experimental de energía y emisiones al aire de Guatemala, 2018–2024

[![Datos: CC BY 4.0](https://img.shields.io/badge/datos-CC%20BY%204.0-1682FC.svg)](LICENSE)
[![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-2EA44F.svg)](LICENSE_CODE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](04_reproduccion_python/instrucciones_reproduccion_python.txt)
[![Reproducción: 47/47 controles](https://img.shields.io/badge/reproducci%C3%B3n-47%2F47%20controles-2EA44F.svg)](05_verificacion/informe_reproduccion_computacional_guatemala_2018_2024.txt)
[![Integridad: 22/22 SHA-256](https://img.shields.io/badge/integridad-22%2F22%20SHA--256-2EA44F.svg)](manifiesto_archivos.txt)

Cuenta de flujos físicos de energía y emisiones al aire para Guatemala,
con cobertura anual de 2018 a 2024. El producto organiza la oferta y la
utilización de productos energéticos mediante una **tabla física de oferta y
utilización (PSUT)**, vincula los flujos con industrias y hogares, y estima
emisiones directas por gas. Su marco conceptual es el **SEEA‑Energy** de
Naciones Unidas.

> [!WARNING]
> **Los resultados tienen carácter experimental y no constituyen una
> estadística oficial.**

> [!NOTE]
> Los agregados de emisiones de 2023 y 2024 incorporan aproximaciones
> identificadas como `PRX`. La actividad energética procede de la PSUT de cada
> año; la aproximación recae en los factores de emisión o, para agricultura, en
> la prolongación del resultado. El estado de cada registro se conserva en el
> conjunto de datos.

La descripción técnica completa y canónica se conserva en
[`readme.txt`](readme.txt). Este `README.md` funciona como portada navegable de
GitHub y no sustituye el inventario de integridad del paquete. El manifiesto
verifica los 22 archivos externos a sí mismo que integran el paquete de
publicación; esta portada es una capa editorial exclusiva del repositorio.

## Autores

| Autor | Afiliación | ORCID |
|---|---|---|
| Juan Alejandro Osorio | Universidad Rafael Landívar | [0009-0001-4260-772X](https://orcid.org/0009-0001-4260-772X) |
| Patricia Villatoro | Universidad Rafael Landívar | [0000-0002-5109-2393](https://orcid.org/0000-0002-5109-2393) |
| Noe Salguero | Universidad Rafael Landívar | [0009-0004-5017-6538](https://orcid.org/0009-0004-5017-6538) |
| José Carlos Soberanis | Universidad de San Carlos de Guatemala, Centro Universitario de Occidente | [0009-0007-0279-4472](https://orcid.org/0009-0007-0279-4472) |

Los roles CRediT de autoría, colaboración y revisión técnica se documentan
en [`creditos.txt`](creditos.txt).

## Qué contiene

| Componente | Contenido | Acceso directo |
|---|---|---|
| Trazabilidad | Registro estructurado de las fuentes y su procedencia | [`registro_fuentes_psut_guatemala.xlsx`](00_trazabilidad_fuentes/registro_fuentes_psut_guatemala.xlsx) |
| Metodología | Marco general, compilación de la PSUT y cuenta de emisiones | [`01_metodologia/`](01_metodologia/) |
| Resultados | PSUT de energía y cuenta de emisiones al aire, 2018–2024 | [`02_resultados_y_diccionario/`](02_resultados_y_diccionario/) |
| Diccionario | Definiciones, campos, códigos y estados de los datos | [`diccionario_datos_guatemala_2018_2024.txt`](02_resultados_y_diccionario/diccionario_datos_guatemala_2018_2024.txt) |
| Modelo tabular | Libro de cálculo con fórmulas y trazabilidad | [`modelo_psut_energia_emisiones_guatemala_2018_2024.xlsx`](03_modelo_hoja_calculo/modelo_psut_energia_emisiones_guatemala_2018_2024.xlsx) |
| Reproducción | Insumo derivado, generador, validador y dependencias | [`04_reproduccion_python/`](04_reproduccion_python/) |
| Cuaderno visor | Consulta anual, indicadores y gráficas sin recalcular las cuentas | [Abrir el cuaderno](04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb) |
| Verificación | Evidencia de la reproducción y huellas digitales | [`informe_reproduccion_computacional_guatemala_2018_2024.txt`](05_verificacion/informe_reproduccion_computacional_guatemala_2018_2024.txt) |

Los dos conjuntos finales son:

- [`psut_energia_guatemala_2018_2024.csv`](02_resultados_y_diccionario/psut_energia_guatemala_2018_2024.csv), con 617 registros de oferta y utilización de energía en terajulios;
- [`cuenta_emisiones_aire_guatemala_2018_2024.csv`](02_resultados_y_diccionario/cuenta_emisiones_aire_guatemala_2018_2024.csv), con 374 registros de emisiones y estados de cálculo.

Los CSV están codificados en UTF‑8, usan punto decimal y no incluyen
separador de millares.

## Resultados clave

| Indicador de verificación | Resultado |
|---|---:|
| Registros del insumo consolidado y validados | 3 446 |
| Registros PSUT generados | 617 |
| Registros de emisiones generados | 374 |
| Cobertura temporal | 2018–2024 |
| Controles independientes aprobados | **47 de 47** |
| Diferencia máxima de cierre de la PSUT | < 10⁻⁶ TJ |
| Diferencia máxima de la identidad de CO₂e | < 10⁻⁹ kt |

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
`CO₂e = CO₂ fósil + 28 × CH₄ + 265 × N₂O`. El CO₂ biogénico se
presenta como partida informativa y no se suma al CO₂ fósil. Consulte el
[`informe de reproducción`](05_verificacion/informe_reproduccion_computacional_guatemala_2018_2024.txt)
para conocer las tolerancias, el entorno y el alcance exacto de la prueba.

## Inicio rápido

El generador y el validador utilizan exclusivamente la biblioteca estándar de
Python. Se requiere **Python 3.10 o posterior**.

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

Una ejecución conforme devuelve código de salida `0`. En el entorno documentado,
el validador aprobó 47 de 47 controles y los dos CSV coincidieron byte a byte
con las referencias. En otros entornos, la conformidad debe juzgarse mediante
los controles estructurales y numéricos, no mediante una expectativa general de
identidad binaria.

Las instrucciones ampliadas están en
[`instrucciones_reproduccion_python.txt`](04_reproduccion_python/instrucciones_reproduccion_python.txt).

## Cuaderno visor

[![Abrir cuaderno visor](https://img.shields.io/badge/Jupyter-abrir%20cuaderno-F37626.svg?logo=jupyter&logoColor=white)](04_reproduccion_python/cuaderno_psut_energia_emisiones_guatemala_2018_2024.ipynb)

El cuaderno es una interfaz de consulta de los dos CSV finales; **no reemplaza
al generador**. Permite seleccionar cualquier año entre 2018 y 2024 y presenta:

- una PSUT integrada de 22 filas conceptuales;
- una vista integrada de emisiones;
- ocho indicadores principales y seis complementarios; y
- once gráficas independientes.

Sus siete celdas técnicas permanecen plegadas de forma predeterminada. El
cuaderno no lee el archivo de entrada, no importa el script de reproducción y
no escribe archivos. Para ejecutarlo en un entorno Jupyter se requieren las
versiones indicadas en
[`requirements.txt`](04_reproduccion_python/requirements.txt); para consultarlo
en GitHub basta abrir el enlace anterior.

## Estructura del repositorio

```text
.
├── 00_trazabilidad_fuentes/       # Registro estructurado de fuentes
├── 01_metodologia/               # Notas metodológicas
├── 02_resultados_y_diccionario/  # CSV finales y diccionario
├── 03_modelo_hoja_calculo/       # Modelo tabular reproducible
├── 04_reproduccion_python/       # Insumo, scripts y cuaderno visor
├── 05_verificacion/              # Informe de reproducción
├── CITATION.cff                 # Metadatos de citación
├── LICENSE                      # Datos y documentación: CC BY 4.0
├── LICENSE_CODE                 # Código: MIT
├── manifiesto_archivos.txt      # Inventario y SHA-256
└── readme.txt                   # Descripción técnica canónica
```

El [`manifiesto_archivos.txt`](manifiesto_archivos.txt) documenta el tamaño y
la huella SHA‑256 de cada archivo del paquete final. Los documentos y datos de
fuente primaria no se redistribuyen.

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
> Guatemala, 2018–2024*, v1.0.0. CC BY 4.0.

No se consigna un DOI mientras no exista un depósito publicado que lo asigne.

## Licencias

El repositorio emplea licenciamiento mixto:

| Material | Licencia |
|---|---|
| Datos derivados, documentación, notas, metadatos, libro de cálculo, tablas y figuras originales | [CC BY 4.0](LICENSE) |
| Código Python y celdas ejecutables originales del cuaderno | [MIT](LICENSE_CODE) |
| Texto, tablas, figuras y resultados guardados en el cuaderno | [CC BY 4.0](LICENSE) |

Los materiales de terceros y las fuentes primarias conservan sus derechos y
condiciones de uso de origen; este producto no los relicencia.

---

**Versión 1.0.0 · Guatemala · cobertura 2018–2024**
