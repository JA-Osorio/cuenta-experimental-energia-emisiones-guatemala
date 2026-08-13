Cuenta experimental de energía y emisiones al aire de Guatemala, 2018–2024

AUTORES

- Juan Alejandro Osorio
- Patricia Villatoro
- Noe Salguero
- José Carlos Soberanis

Las afiliaciones, los identificadores ORCID y los demás créditos se presentan
en creditos.txt.

1. RESUMEN

Este producto presenta una cuenta experimental de flujos físicos de energía y de emisiones al aire para Guatemala durante 2018–2024. La cuenta organiza anualmente la oferta y el uso de productos energéticos, vincula los flujos con sectores económicos y hogares, y estima emisiones directas por gas a partir de la actividad energética observada.

El marco conceptual se basa en el Sistema de Contabilidad Ambiental y Económica para la Energía. Los balances energéticos nacionales del Ministerio de Energía y Minas constituyen la referencia principal para los flujos físicos. Los resultados tienen carácter experimental y no constituyen una estadística oficial.

2. COBERTURA

- Ámbito geográfico: Guatemala.
- Período de referencia: 2018–2024.
- Unidades energéticas: kBEP y terajulios (TJ).
- Unidades de emisiones: kilotoneladas por gas y kilotoneladas de dióxido de carbono equivalente (kt CO₂e).
- Gases: CO₂, CH₄ y N₂O, con separación entre CO₂ fósil y CO₂ biogénico cuando corresponde.
- Agentes: industrias, hogares, ambiente y resto del mundo, según la disponibilidad de las fuentes.
- Cobertura temática: energía primaria y secundaria, transformación, consumo sectorial, emisiones asociadas con la energía y un módulo diferenciado de procesos agrícolas no energéticos.

La CIIU Rev. 4 se utiliza como referencia para interpretar las actividades,
pero la cuenta conserva los agregados físicos realmente observados en las
fuentes. Cuando no existe una apertura reproducible, no se crean sectores
mediante ponderadores externos. Por ello, el consumo que la fuente publica de
forma agregada como Industria se conserva íntegramente en esa categoría.

3. COMPONENTES DEL PRODUCTO

3.1 PSUT de energía

La tabla de oferta y utilización física registra productos energéticos, flujos de recursos naturales, transformación, consumo intermedio, consumo final y relaciones con el ambiente. Los registros se expresan en TJ y mantienen la correspondencia con los totales publicados por el Balance Energético Nacional.

3.2 Emisiones al aire

La cuenta de emisiones integra la actividad energética con factores de emisión por gas y clase de combustible. La electricidad se registra en el sector consumidor como uso de energía, mientras las emisiones de su generación permanecen en las industrias de energía. El CO₂ biogénico se presenta como partida informativa y no se suma al CO₂ fósil.

3.3 Datos y parámetros

Los datos de entrada conservan la relación entre productos de las fuentes, códigos normalizados, sectores de la cuenta, lados de oferta y uso, y categorías de emisiones. Los factores de conversión, factores de emisión, coeficientes, potenciales de calentamiento global y reglas de asignación se identifican de manera explícita.

4. FUENTES Y MÉTODO

Las fuentes principales son:

- Balances Energéticos Nacionales del Ministerio de Energía y Minas, 2018–2024.
- Tablas Comunes de Reporte de Guatemala y documentación de la CMNUCC, con información disponible hasta 2022.
- Referencias de Naciones Unidas, UNSD, OLADE e IPCC para conceptos, clasificaciones, unidades y métodos.
- Información de AMM, CNEE, BANGUAT, SAT, INE, INAB, CPN y otras instituciones nacionales utilizada para contraste sectorial y documental.

Cada observación conserva un identificador de procedencia, la fuente, la tabla o categoría, la unidad original y la transformación aplicada.

La conversión energética utiliza el factor:

Energía [TJ] = valor [kBEP] × 5,81 [TJ/kBEP]

Las emisiones directas se estiman por sector s, producto p, gas g y año t:

Emisiones(g,s,p,t) [kt] = Energía(s,p,t) [TJ] × FE(g,c,t) [kg/TJ] ÷ 1 000 000

Para 2018–2022 se emplean factores implícitos derivados de información oficial del mismo año. En 2023–2024, la actividad energética continúa procediendo de la PSUT de cada año, pero los factores de emisión corresponden a 2022 y se identifican como PRX; las emisiones agrícolas se prolongan desde 2022 mediante el valor agregado bruto y su resultado también se identifica como PRX. En consecuencia, el 100 % del CO₂e cuantificado en 2023 y en 2024 depende de registros cuyo estado_factor o estado_resultado es PRX. Esta condición identifica una aproximación explícita en el factor o en el resultado; no implica que la actividad energética registrada en la PSUT haya sido inventada o imputada.

Para agregar los gases se utilizaron potenciales de calentamiento global a 100 años del Quinto Informe de Evaluación del IPCC (AR5), sin retroalimentación clima–carbono: 1 para CO₂, 28 para CH₄ y 265 para N₂O (IPCC, 2013, tabla 8.7). El indicador de CO₂ equivalente se calcula de forma uniforme:

CO₂e [kt] = CO₂ fósil [kt] + 28 × CH₄ [kt] + 265 × N₂O [kt]

Los balances de oferta y uso, las asignaciones sectoriales y las emisiones se verifican mediante conciliaciones numéricas y reglas metodológicas explícitas.

5. ESTRUCTURA DE LOS DATOS

Los datos se organizan en tablas relacionadas mediante identificadores estables. Las vistas permiten seleccionar cualquiera de los años comprendidos entre 2018 y 2024.

- Procedencia: source_record_id, institución, documento, tabla, página, categoría, unidad y valor original.
- Productos: código original, código normalizado, nombre, clase energética y unidad.
- Flujos de energía: año, producto, bloque, lado de oferta o uso, agente, sector y valor en TJ.
- Emisiones: año, sector, producto, categoría, gas, tipo de CO₂, actividad, factor de emisión, unidad y emisión calculada.
- Parámetros: factores de conversión, factores implícitos anuales, potenciales de calentamiento global, tolerancias, coeficientes y reglas de asignación.
- Validaciones: diferencias de balance, cobertura de registros y consistencia entre tablas relacionadas.

En documentos y visualizaciones, los valores numéricos emplean coma decimal y espacio para separar millares. Los archivos CSV utilizan punto decimal, no incluyen separador de millares y se codifican en UTF-8 para facilitar su lectura con Python y otras herramientas. Las unidades acompañan cada variable cuantitativa.

6. REPRODUCCIÓN

El producto incluye un script de reproducción y un cuaderno de consulta. El
script transforma el archivo datos_modelo_guatemala_2018_2024.csv en los dos
datasets finales. El cuaderno carga esos dos resultados para consultar la PSUT,
seleccionar el año, examinar indicadores y visualizar las series, sin repetir el
cálculo del script.

El script de reproducción comprende:

1. lectura de los insumos;
2. normalización de productos, unidades y sectores;
3. conversión de kBEP a TJ;
4. construcción de la tabla de oferta y utilización física;
5. cálculo de emisiones por gas;
6. integración del indicador de CO₂ equivalente;
7. conciliación de resultados; y
8. exportación de las tablas del producto.

El cuaderno utiliza psut_energia_guatemala_2018_2024.csv y
cuenta_emisiones_aire_guatemala_2018_2024.csv. No requiere el archivo de entrada
del modelo ni genera nuevamente las cuentas.

La identidad byte a byte documentada en el informe de reproducción corresponde
exclusivamente al entorno y a las versiones allí consignados. En otros entornos,
la equivalencia debe comprobarse con el validador mediante controles
estructurales y numéricos; no se afirma una identidad binaria general.

7. ALCANCE INTERPRETATIVO

- La cuenta describe flujos físicos de energía y emisiones; no sustituye las cuentas monetarias ni los inventarios oficiales.
- Los agregados sectoriales reflejan la resolución de las fuentes disponibles. No se imputan desagregaciones sin sustento reproducible.
- Cero, no aplica, no estimado, incluido en otra categoría y ausencia de dato son estados diferentes.
- La extracción de un recurso energético se distingue de su combustión posterior.
- El uso de electricidad no genera emisiones directas en el punto de consumo; las emisiones se atribuyen a su generación.
- Las emisiones de biomasa distinguen el CO₂ biogénico de los gases incluidos en el indicador de CO₂ equivalente.
- Las cifras deben interpretarse conforme a las definiciones y alcances de cada tabla.

El alcance de esta publicación se limita a la compilación validada para
2018–2024; no establece un calendario ni un compromiso de actualización.

8. LICENCIA Y CITACIÓN

El licenciamiento se define por tipo de contenido. Los datos derivados, las tablas, las figuras y la documentación original se distribuyen bajo la licencia Creative Commons Atribución 4.0 Internacional (CC BY 4.0). El código Python y las celdas ejecutables originales del cuaderno computacional se distribuyen bajo la licencia MIT. El texto, las tablas, las figuras y los resultados guardados en el cuaderno se rigen por CC BY 4.0.

Los documentos y datos de fuente primaria no forman parte de la distribución pública. Los materiales de terceros no quedan relicenciados por este producto y conservan sus condiciones de uso y derechos de origen. El alcance detallado se especifica en LICENSE y LICENSE_CODE.

La cita normalizada del producto se encuentra en CITATION.cff.
