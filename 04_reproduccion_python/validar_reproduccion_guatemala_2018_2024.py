#!/usr/bin/env python3
"""Validación de la cuenta experimental de energía y emisiones al aire de
Guatemala, 2018–2024.

Autores:
    Juan Alejandro Osorio
    Patricia Villatoro
    Noe Salguero
    José Carlos Soberanis

El programa usa exclusivamente la biblioteca estandar de Python. Compara los
CSV reproducidos con los CSV de referencia por clave y por campo, y comprueba
las invariantes principales del producto de datos.

Ejemplo:

    python validar_reproduccion_guatemala_2018_2024.py \
        --generados ./salida \
        --referencias ../02_resultados_y_diccionario
"""

from __future__ import annotations

import argparse
import csv
import posixpath
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ARCHIVO_PSUT = "psut_energia_guatemala_2018_2024.csv"
ARCHIVO_EMISIONES = "cuenta_emisiones_aire_guatemala_2018_2024.csv"
ANIOS_ESPERADOS = {str(anio) for anio in range(2018, 2025)}

COLUMNAS_PSUT = [
    "registro_mapeo",
    "anio",
    "producto",
    "flow_group",
    "lado",
    "bloque",
    "unidad_sectorial",
    "source_record_id",
    "metodo",
    "ajuste",
    "TJ",
    "tipo_STAT",
    "estado_fuente",
]

COLUMNAS_EMISIONES = [
    "clave_emision",
    "anio",
    "unidad_sectorial_agregada",
    "modulo",
    "categoria_ipcc",
    "categoria_nombre",
    "producto_std",
    "metodo_asignacion",
    "unidad_origen_psut",
    "psut_side",
    "psut_block_code",
    "source_record_id",
    "actividad_base_tj",
    "actividad_emisiones_tj",
    "grupo_factor",
    "tratamiento_co2",
    "anio_factor",
    "estado_factor",
    "ef_co2_kg_tj",
    "ef_ch4_kg_tj",
    "ef_n2o_kg_tj",
    "gas_fuente",
    "emision_fuente_kt_gas",
    "co2_directo_kt",
    "co2_biogenico_memo_kt",
    "ch4_kt",
    "n2o_kt",
    "co2e_kt",
    "estado_resultado",
    "clave_notacion",
    "metodo_calculo",
    "fuente_id_actividad",
    "fuente_id_factor",
    "nota",
]

CAMPOS_NUMERICOS_PSUT = {"TJ"}
CAMPOS_NUMERICOS_EMISIONES = {
    "actividad_base_tj",
    "actividad_emisiones_tj",
    "ef_co2_kg_tj",
    "ef_ch4_kg_tj",
    "ef_n2o_kg_tj",
    "emision_fuente_kt_gas",
    "co2_directo_kt",
    "co2_biogenico_memo_kt",
    "ch4_kt",
    "n2o_kt",
    "co2e_kt",
}

GWP_CH4 = Decimal("28")
GWP_N2O = Decimal("265")
# Precisión del BEN documentada en NT-01: 0,005 kBEP × 5,81 TJ/kBEP.
REDONDEO_CELDA_TJ = Decimal("0.02905")
MAXIMO_EJEMPLOS = 10


@dataclass
class Informe:
    """Acumula comprobaciones y conserva ejemplos breves de las fallas."""

    aprobadas: list[str] = field(default_factory=list)
    fallidas: list[str] = field(default_factory=list)

    def comprobar(self, condicion: bool, nombre: str, detalle: str = "") -> None:
        if condicion:
            self.aprobadas.append(nombre)
            return
        mensaje = nombre if not detalle else f"{nombre}: {detalle}"
        self.fallidas.append(mensaje)

    def mostrar(self) -> None:
        for mensaje in self.aprobadas:
            print(f"[OK] {mensaje}")
        for mensaje in self.fallidas:
            print(f"[FALLO] {mensaje}")
        print()
        if self.fallidas:
            print(
                "RESULTADO: NO APROBADO "
                f"({len(self.fallidas)} fallas; {len(self.aprobadas)} controles aprobados)"
            )
        else:
            print(f"RESULTADO: APROBADO ({len(self.aprobadas)} controles)")


def decimal_positivo(texto: str) -> Decimal:
    """Convierte un argumento en Decimal positivo y finito."""

    try:
        valor = Decimal(texto)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"no es un numero decimal: {texto}") from exc
    if not valor.is_finite() or valor <= 0:
        raise argparse.ArgumentTypeError("la tolerancia debe ser positiva y finita")
    return valor


def leer_csv(ruta: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Lee un CSV UTF-8 y devuelve encabezado y registros."""

    if not ruta.is_file():
        raise FileNotFoundError(f"no se encontro el archivo: {ruta}")
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames is None:
            raise ValueError(f"el archivo no contiene encabezado: {ruta}")
        encabezado = list(lector.fieldnames)
        registros = [dict(fila) for fila in lector]
    return encabezado, registros


def a_decimal(texto: str, contexto: str) -> Decimal:
    """Convierte texto no vacio en un Decimal finito."""

    if texto == "":
        raise ValueError(f"valor numerico vacio en {contexto}")
    try:
        valor = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"valor numerico invalido en {contexto}: {texto!r}") from exc
    if not valor.is_finite():
        raise ValueError(f"valor numerico no finito en {contexto}: {texto!r}")
    return valor


def son_cercanos(
    valor_a: Decimal,
    valor_b: Decimal,
    tolerancia_absoluta: Decimal,
    tolerancia_relativa: Decimal,
) -> bool:
    """Compara dos decimales con tolerancias absoluta y relativa explicitas."""

    limite = max(
        tolerancia_absoluta,
        tolerancia_relativa * max(abs(valor_a), abs(valor_b)),
    )
    return abs(valor_a - valor_b) <= limite


def abreviar(texto: str, longitud: int = 120) -> str:
    if len(texto) <= longitud:
        return texto
    return texto[: longitud - 3] + "..."


def claves_duplicadas(
    registros: Sequence[Mapping[str, str]], clave: str
) -> dict[str, int]:
    conteo = Counter(fila.get(clave, "") for fila in registros)
    return {valor: cantidad for valor, cantidad in conteo.items() if cantidad > 1}


def indexar(
    registros: Sequence[Mapping[str, str]], clave: str
) -> dict[str, Mapping[str, str]]:
    indice: dict[str, Mapping[str, str]] = {}
    for fila in registros:
        indice.setdefault(fila.get(clave, ""), fila)
    return indice


def detalle_elementos(elementos: Iterable[object]) -> str:
    muestra = list(elementos)[:MAXIMO_EJEMPLOS]
    return "; ".join(abreviar(repr(elemento)) for elemento in muestra)


def comparar_archivo(
    nombre: str,
    encabezado_generado: Sequence[str],
    generados: Sequence[Mapping[str, str]],
    encabezado_referencia: Sequence[str],
    referencias: Sequence[Mapping[str, str]],
    clave: str,
    campos_numericos: set[str],
    tolerancia_absoluta: Decimal,
    tolerancia_relativa: Decimal,
    informe: Informe,
) -> None:
    """Compara dos tablas por clave; el orden de las filas no altera el resultado."""

    mismo_encabezado = list(encabezado_generado) == list(encabezado_referencia)
    informe.comprobar(
        mismo_encabezado,
        f"{nombre}: encabezado identico a la referencia",
        "el orden o el conjunto de columnas difiere",
    )
    if not mismo_encabezado:
        return

    duplicados_generados = claves_duplicadas(generados, clave)
    duplicados_referencia = claves_duplicadas(referencias, clave)
    informe.comprobar(
        not duplicados_generados,
        f"{nombre}: 0 claves duplicadas en el archivo generado",
        detalle_elementos(sorted(duplicados_generados.items())),
    )
    informe.comprobar(
        not duplicados_referencia,
        f"{nombre}: 0 claves duplicadas en la referencia",
        detalle_elementos(sorted(duplicados_referencia.items())),
    )

    indice_generado = indexar(generados, clave)
    indice_referencia = indexar(referencias, clave)
    faltantes = sorted(set(indice_referencia) - set(indice_generado))
    adicionales = sorted(set(indice_generado) - set(indice_referencia))
    informe.comprobar(
        not faltantes,
        f"{nombre}: 0 claves faltantes",
        detalle_elementos(faltantes),
    )
    informe.comprobar(
        not adicionales,
        f"{nombre}: 0 claves adicionales",
        detalle_elementos(adicionales),
    )

    diferencias: list[str] = []
    for valor_clave in sorted(set(indice_generado) & set(indice_referencia)):
        fila_generada = indice_generado[valor_clave]
        fila_referencia = indice_referencia[valor_clave]
        for campo in encabezado_referencia:
            generado = fila_generada.get(campo, "")
            referencia = fila_referencia.get(campo, "")
            if campo in campos_numericos:
                if generado == "" or referencia == "":
                    iguales = generado == referencia
                else:
                    try:
                        numero_generado = a_decimal(
                            generado, f"{nombre}/{valor_clave}/{campo}"
                        )
                        numero_referencia = a_decimal(
                            referencia, f"referencia/{valor_clave}/{campo}"
                        )
                        iguales = son_cercanos(
                            numero_generado,
                            numero_referencia,
                            tolerancia_absoluta,
                            tolerancia_relativa,
                        )
                    except ValueError:
                        iguales = False
            else:
                iguales = generado == referencia
            if not iguales and len(diferencias) < MAXIMO_EJEMPLOS:
                diferencias.append(
                    f"{valor_clave}/{campo}: generado={abreviar(generado)!r}, "
                    f"referencia={abreviar(referencia)!r}"
                )

    informe.comprobar(
        not diferencias,
        f"{nombre}: todos los campos coinciden por clave",
        "; ".join(diferencias),
    )


def validar_esquema(
    nombre: str,
    encabezado: Sequence[str],
    esperado: Sequence[str],
    informe: Informe,
) -> None:
    informe.comprobar(
        list(encabezado) == list(esperado),
        f"{nombre}: esquema y orden de columnas esperados",
        f"obtenido={list(encabezado)!r}",
    )


def validar_psut(
    etiqueta: str,
    encabezado: Sequence[str],
    registros: Sequence[Mapping[str, str]],
    tolerancia_cierre: Decimal,
    informe: Informe,
) -> None:
    """Comprueba estructura, cobertura, NO_ASIG y cierres de la PSUT."""

    validar_esquema(f"PSUT {etiqueta}", encabezado, COLUMNAS_PSUT, informe)
    informe.comprobar(
        len(registros) == 617,
        f"PSUT {etiqueta}: 617 registros",
        f"obtenidos={len(registros)}",
    )
    anios = {fila.get("anio", "") for fila in registros}
    informe.comprobar(
        anios == ANIOS_ESPERADOS,
        f"PSUT {etiqueta}: cobertura anual 2018-2024",
        f"obtenidos={sorted(anios)!r}",
    )
    duplicados = claves_duplicadas(registros, "registro_mapeo")
    informe.comprobar(
        not duplicados,
        f"PSUT {etiqueta}: 0 registros_mapeo duplicados",
        detalle_elementos(sorted(duplicados.items())),
    )

    no_asig_observado = Counter(
        (fila.get("anio", ""), fila.get("producto", ""))
        for fila in registros
        if fila.get("unidad_sectorial") == "NO_ASIG"
    )
    no_asig_esperado = Counter(
        [(anio, "NOEN") for anio in sorted(ANIOS_ESPERADOS)]
        + [("2019", "GAS")]
    )
    informe.comprobar(
        no_asig_observado == no_asig_esperado,
        f"PSUT {etiqueta}: NO_ASIG contiene 7 NOEN y GAS 2019",
        f"obtenido={sorted(no_asig_observado.items())!r}",
    )

    totales: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(
        lambda: {"Supply": Decimal(0), "Use": Decimal(0)}
    )
    lados_por_grupo: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    errores_numericos: list[str] = []
    lados_invalidos: list[str] = []
    for fila in registros:
        clave_grupo = (
            fila.get("anio", ""),
            fila.get("producto", ""),
            fila.get("flow_group", ""),
        )
        lado = fila.get("lado", "")
        if lado not in {"Supply", "Use"}:
            if len(lados_invalidos) < MAXIMO_EJEMPLOS:
                lados_invalidos.append(
                    f"{fila.get('registro_mapeo', '')}: {lado!r}"
                )
            continue
        try:
            valor = a_decimal(
                fila.get("TJ", ""), f"PSUT/{fila.get('registro_mapeo', '')}/TJ"
            )
        except ValueError as exc:
            if len(errores_numericos) < MAXIMO_EJEMPLOS:
                errores_numericos.append(str(exc))
            continue
        totales[clave_grupo][lado] += valor
        lados_por_grupo[clave_grupo].add(lado)

    informe.comprobar(
        not lados_invalidos,
        f"PSUT {etiqueta}: lados validos",
        "; ".join(lados_invalidos),
    )
    informe.comprobar(
        not errores_numericos,
        f"PSUT {etiqueta}: valores TJ validos y finitos",
        "; ".join(errores_numericos),
    )

    # Un grupo con un unico lado es admisible solo si el valor de ese lado es
    # cero; en ese caso, el lado ausente representa tambien un cero implicito.
    grupos_incompletos = sorted(
        clave
        for clave, lados in lados_por_grupo.items()
        if lados != {"Supply", "Use"}
        and (
            abs(totales[clave]["Supply"]) > tolerancia_cierre
            or abs(totales[clave]["Use"]) > tolerancia_cierre
        )
    )
    informe.comprobar(
        not grupos_incompletos,
        f"PSUT {etiqueta}: cada grupo no nulo tiene oferta y uso",
        detalle_elementos(grupos_incompletos),
    )

    residuos: list[tuple[tuple[str, str, str], Decimal]] = []
    for clave_grupo, lados in totales.items():
        residuo = lados["Supply"] - lados["Use"]
        if abs(residuo) > tolerancia_cierre:
            residuos.append((clave_grupo, residuo))
    residuos.sort(key=lambda elemento: abs(elemento[1]), reverse=True)
    informe.comprobar(
        not residuos,
        f"PSUT {etiqueta}: 0 residuos estadisticos finales por producto-anio-grupo",
        detalle_elementos(residuos),
    )

    cantidades = Counter(
        (fila.get("anio"), fila.get("producto"))
        for fila in registros
        if fila.get("flow_group") == "Energy products"
        and fila.get("unidad_sectorial") != "STAT"
    )
    errores_stat = []
    for fila in registros:
        if fila.get("unidad_sectorial") != "STAT":
            continue
        limite = cantidades[(fila.get("anio"), fila.get("producto"))] * REDONDEO_CELDA_TJ
        try:
            valor = a_decimal(fila.get("TJ", ""), f"STAT/{fila.get('registro_mapeo', '')}")
            correcto = abs(valor) <= limite and fila.get("tipo_STAT") == "redondeo"
        except ValueError:
            correcto = False
        if not correcto:
            errores_stat.append((fila.get("registro_mapeo"), fila.get("TJ"), str(limite)))
    informe.comprobar(
        not errores_stat,
        f"PSUT {etiqueta}: STAT respeta el limite de redondeo antes del cierre",
        detalle_elementos(errores_stat),
    )


def validar_emisiones(
    etiqueta: str,
    encabezado: Sequence[str],
    registros: Sequence[Mapping[str, str]],
    tolerancia_emisiones: Decimal,
    informe: Informe,
) -> dict[str, Decimal]:
    """Comprueba gases, disponibilidad y subtotal CO2e sin CO2 biogenico."""

    validar_esquema(
        f"Emisiones {etiqueta}", encabezado, COLUMNAS_EMISIONES, informe
    )
    informe.comprobar(
        len(registros) == 374,
        f"Emisiones {etiqueta}: 374 registros",
        f"obtenidos={len(registros)}",
    )
    anios = {fila.get("anio", "") for fila in registros}
    informe.comprobar(
        anios == ANIOS_ESPERADOS,
        f"Emisiones {etiqueta}: cobertura anual 2018-2024",
        f"obtenidos={sorted(anios)!r}",
    )
    duplicados = claves_duplicadas(registros, "clave_emision")
    informe.comprobar(
        not duplicados,
        f"Emisiones {etiqueta}: 0 claves_emision duplicadas",
        detalle_elementos(sorted(duplicados.items())),
    )

    campos_identidad = [
        "co2_directo_kt",
        "co2_biogenico_memo_kt",
        "ch4_kt",
        "n2o_kt",
        "co2e_kt",
    ]
    errores_presencia: list[str] = []
    errores_numericos: list[str] = []
    errores_identidad: list[tuple[str, Decimal]] = []
    errores_factores: list[str] = []
    errores_estados: list[str] = []
    errores_ceros: list[str] = []
    totales_co2e = {anio: Decimal(0) for anio in ANIOS_ESPERADOS}
    totales_componentes = {
        anio: {
            "co2_directo": Decimal(0),
            "ch4": Decimal(0),
            "n2o": Decimal(0),
            "biogenico": Decimal(0),
        }
        for anio in ANIOS_ESPERADOS
    }

    for fila in registros:
        clave = fila.get("clave_emision", "")
        anio = fila.get("anio", "")
        try:
            valores = {
                campo: None if fila.get(campo, "") == "" else a_decimal(fila[campo], f"Emisiones/{clave}/{campo}")
                for campo in campos_identidad
            }
            if fila.get("modulo") != "AGRICULTURA":
                actividad = a_decimal(fila.get("actividad_emisiones_tj", ""), f"Emisiones/{clave}/actividad")
                factores = {
                    gas: None if fila.get(f"ef_{gas.lower()}_kg_tj", "") == "" else a_decimal(
                        fila[f"ef_{gas.lower()}_kg_tj"], f"Emisiones/{clave}/factor_{gas}"
                    ) for gas in ("CO2", "CH4", "N2O")
                }
                ausentes = [gas for gas, factor in factores.items() if factor is None]
                esperados = {
                    gas: None if factor is None else actividad * factor / Decimal("1000000")
                    for gas, factor in factores.items()
                }
                biogenico = fila.get("tratamiento_co2") == "BIOGENICO"
                campos_gas = {
                    "co2_directo_kt": None if esperados["CO2"] is None else (Decimal(0) if biogenico else esperados["CO2"]),
                    "co2_biogenico_memo_kt": None if esperados["CO2"] is None else (esperados["CO2"] if biogenico else Decimal(0)),
                    "ch4_kt": esperados["CH4"], "n2o_kt": esperados["N2O"],
                }
                for campo, esperado in campos_gas.items():
                    obtenido = valores[campo]
                    if esperado is None or obtenido is None:
                        correcto = esperado is None and obtenido is None
                    else:
                        correcto = son_cercanos(obtenido, esperado, tolerancia_emisiones, Decimal("1e-12"))
                    if not correcto:
                        errores_factores.append(f"{clave}/{campo}: valor={obtenido}, actividad x factor={esperado}")
                hay_factores = len(ausentes) < 3
                if (valores["co2e_kt"] is not None) != hay_factores:
                    errores_presencia.append(clave)
                if ausentes:
                    estado_esperado = "PARCIAL" if hay_factores else "SIN_DATO"
                    codigos = ";".join(f"{gas}:SIN_DATO" for gas in ausentes)
                    if (
                        fila.get("estado_resultado") != estado_esperado
                        or fila.get("clave_notacion") != codigos
                        or "código interno" not in fila.get("nota", "")
                        or (hay_factores and "subtotal" not in fila.get("nota", "").lower())
                        or (not hay_factores and (
                            fila.get("estado_factor") != "SIN_DATO"
                            or fila.get("metodo_calculo") != "SIN_CALCULO_SIN_DATO"
                        ))
                    ):
                        errores_estados.append(clave)
                elif fila.get("estado_resultado") in {"PARCIAL", "SIN_DATO"}:
                    errores_estados.append(clave)
                if fila.get("grupo_factor") == "CERO_DIRECTO":
                    if (
                        any(valor != 0 for valor in factores.values())
                        or any(valor != 0 for valor in valores.values())
                        or fila.get("fuente_id_factor") != "METODO_EMISIONES"
                        or fila.get("estado_factor") != "CAL"
                        or fila.get("estado_resultado") != "CAL"
                        or fila.get("metodo_calculo") != "CERO_DIRECTO"
                    ):
                        errores_ceros.append(clave)
            else:
                presentes = [valor is not None for valor in valores.values()]
                if any(presentes) and not all(presentes):
                    errores_presencia.append(clave)
        except ValueError as exc:
            if len(errores_numericos) < MAXIMO_EJEMPLOS:
                errores_numericos.append(str(exc))
            continue

        if valores["co2e_kt"] is None:
            continue
        # Solo para sumar el subtotal: no se rellenan los campos publicados.
        co2_directo = valores["co2_directo_kt"] or Decimal(0)
        co2_biogenico = valores["co2_biogenico_memo_kt"] or Decimal(0)
        ch4 = valores["ch4_kt"] or Decimal(0)
        n2o = valores["n2o_kt"] or Decimal(0)
        co2e = valores["co2e_kt"]

        # El CO2 biogenico se mantiene como partida informativa y no entra en CO2e.
        co2e_calculado = co2_directo + GWP_CH4 * ch4 + GWP_N2O * n2o
        diferencia = co2e - co2e_calculado
        if abs(diferencia) > tolerancia_emisiones:
            errores_identidad.append((clave, diferencia))
        if anio in totales_co2e:
            totales_co2e[anio] += co2e
            totales_componentes[anio]["co2_directo"] += co2_directo
            totales_componentes[anio]["ch4"] += ch4
            totales_componentes[anio]["n2o"] += n2o
            totales_componentes[anio]["biogenico"] += co2_biogenico

    informe.comprobar(
        not errores_presencia,
        f"Emisiones {etiqueta}: subtotal presente solo con componentes cuantificados",
        detalle_elementos(errores_presencia),
    )
    informe.comprobar(
        not errores_numericos,
        f"Emisiones {etiqueta}: valores de la identidad validos y finitos",
        "; ".join(errores_numericos),
    )
    informe.comprobar(
        not errores_factores,
        f"Emisiones {etiqueta}: cada gas respeta actividad por factor y ausencia de dato",
        detalle_elementos(errores_factores),
    )
    informe.comprobar(
        not errores_estados,
        f"Emisiones {etiqueta}: subtotales y ausencias identificados por gas",
        detalle_elementos(errores_estados),
    )
    informe.comprobar(
        not errores_ceros,
        f"Emisiones {etiqueta}: ceros metodologicos trazados a METODO_EMISIONES",
        detalle_elementos(errores_ceros),
    )
    errores_identidad.sort(key=lambda elemento: abs(elemento[1]), reverse=True)
    informe.comprobar(
        not errores_identidad,
        f"Emisiones {etiqueta}: identidad CO2e excluye CO2 biogenico",
        detalle_elementos(errores_identidad),
    )

    errores_totales: list[tuple[str, Decimal]] = []
    for anio in sorted(ANIOS_ESPERADOS):
        componentes = totales_componentes[anio]
        total_calculado = (
            componentes["co2_directo"]
            + GWP_CH4 * componentes["ch4"]
            + GWP_N2O * componentes["n2o"]
        )
        diferencia = totales_co2e[anio] - total_calculado
        if abs(diferencia) > tolerancia_emisiones:
            errores_totales.append((anio, diferencia))
    informe.comprobar(
        not errores_totales,
        f"Emisiones {etiqueta}: identidad CO2e satisfecha en los 7 totales anuales",
        detalle_elementos(errores_totales),
    )
    return totales_co2e


def comparar_totales_anuales(
    generados: Mapping[str, Decimal],
    referencias: Mapping[str, Decimal],
    tolerancia: Decimal,
    informe: Informe,
) -> None:
    diferencias: list[tuple[str, Decimal]] = []
    for anio in sorted(ANIOS_ESPERADOS):
        diferencia = generados.get(anio, Decimal(0)) - referencias.get(
            anio, Decimal(0)
        )
        if abs(diferencia) > tolerancia:
            diferencias.append((anio, diferencia))
    informe.comprobar(
        not diferencias,
        "Emisiones: los 7 totales anuales reproducen la referencia",
        detalle_elementos(diferencias),
    )


def validar_gas_natural_excel(
    ruta: Path,
    psut: Sequence[Mapping[str, str]],
    tolerancia: Decimal,
    informe: Informe,
) -> None:
    """Coteja solo GN en la vista PSUT anual con los CSV, sin recalcular Excel."""

    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    relacion_id = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with zipfile.ZipFile(ruta) as archivo:
        relaciones = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in ET.fromstring(archivo.read("xl/_rels/workbook.xml.rels"))
        }
        libro = ET.fromstring(archivo.read("xl/workbook.xml"))
        hojas = libro.find("s:sheets", ns)
        hoja = next((item for item in hojas if item.attrib.get("name") == "PSUT"), None) if hojas is not None else None
        if hoja is None:
            raise ValueError("El libro no contiene una hoja PSUT.")
        destino = relaciones[hoja.attrib[relacion_id]]
        destino = destino.lstrip("/") if destino.startswith("/") else posixpath.normpath("xl/" + destino)
        cadenas = []
        if "xl/sharedStrings.xml" in archivo.namelist():
            cadenas = [
                "".join(nodo.itertext())
                for nodo in ET.fromstring(archivo.read("xl/sharedStrings.xml"))
            ]
        raiz = ET.fromstring(archivo.read(destino))
        valores: dict[str, str] = {}
        formulas: dict[str, str] = {}
        for celda in raiz.findall(".//s:c", ns):
            coordenada = celda.attrib["r"]
            valor = celda.findtext("s:v", "", ns)
            if celda.attrib.get("t") == "s":
                valor = cadenas[int(valor)]
            elif celda.find("s:is", ns) is not None:
                valor = "".join(celda.find("s:is", ns).itertext())
            valores[coordenada] = valor
            formulas[coordenada] = celda.findtext("s:f", "", ns)

    filas_gn = [
        int(coordenada[1:])
        for coordenada, valor in valores.items()
        if coordenada.startswith("A") and coordenada[1:].isdigit() and valor == "GN"
        and any(
            "Energy products" in formula and celda.rstrip("0123456789") != celda
            and celda[len(celda.rstrip("0123456789")):] == coordenada[1:]
            for celda, formula in formulas.items()
        )
    ]
    informe.comprobar(
        len(filas_gn) == 1,
        "Excel PSUT: GN aparece una vez entre los productos energeticos",
        f"filas={filas_gn}",
    )
    if len(filas_gn) != 1:
        return
    fila_gn = filas_gn[0]
    anio = valores.get("B3", "")
    cabeceras = [
        int(coordenada[1:]) for coordenada, valor in valores.items()
        if coordenada.startswith("A") and coordenada[1:].isdigit()
        and valor == "Código" and int(coordenada[1:]) < fila_gn
    ]
    if not cabeceras or anio not in ANIOS_ESPERADOS:
        raise ValueError("La vista PSUT no identifica el año o las unidades de GN.")
    fila_cabecera = max(cabeceras)
    diferencias = []
    # Columnas de suministro y utilización del formato publicado del libro.
    for lado, columnas in (("Supply", "CDEFGH"), ("Use", "JKLMNOPQRSTU")):
        for columna in columnas:
            unidad = valores.get(f"{columna}{fila_cabecera}", "")
            filas = [
                item for item in psut
                if item.get("anio") == anio and item.get("producto") == "GN"
                and item.get("flow_group") == "Energy products"
                and item.get("lado") == lado and item.get("unidad_sectorial") == unidad
            ]
            celda = f"{columna}{fila_gn}"
            obtenido = valores.get(celda, "")
            if not filas:
                correcto = obtenido == ""
                esperado = None
            else:
                esperado = sum((a_decimal(item["TJ"], "PSUT/GN") for item in filas), Decimal(0))
                correcto = obtenido != "" and abs(a_decimal(obtenido, f"Excel/{celda}") - esperado) <= tolerancia
            if not correcto:
                diferencias.append((celda, obtenido, esperado))
    informe.comprobar(
        not diferencias,
        "Excel PSUT: valores almacenados de GN coinciden con el CSV del año seleccionado",
        detalle_elementos(diferencias),
    )


def crear_argumentos() -> argparse.ArgumentParser:
    directorio_script = Path(__file__).resolve().parent
    analizador = argparse.ArgumentParser(
        description=(
            "Compara los CSV reproducidos con las referencias y verifica "
            "las invariantes de la PSUT y la cuenta de emisiones."
        )
    )
    analizador.add_argument(
        "--generados",
        type=Path,
        default=directorio_script,
        help="directorio que contiene los dos CSV reproducidos",
    )
    analizador.add_argument(
        "--referencias",
        type=Path,
        default=directorio_script.parent / "02_resultados_y_diccionario",
        help="directorio que contiene los dos CSV finales de referencia",
    )
    analizador.add_argument(
        "--modelo-excel", type=Path,
        help="opcional: coteja GN en la vista PSUT del XLSX mediante sus valores almacenados",
    )
    analizador.add_argument(
        "--tolerancia-campos",
        type=decimal_positivo,
        default=Decimal("1e-9"),
        help="tolerancia absoluta para comparar campos numericos (1e-9)",
    )
    analizador.add_argument(
        "--tolerancia-relativa",
        type=decimal_positivo,
        default=Decimal("1e-12"),
        help="tolerancia relativa para comparar campos numericos (1e-12)",
    )
    analizador.add_argument(
        "--tolerancia-cierre-tj",
        type=decimal_positivo,
        default=Decimal("1e-6"),
        help="tolerancia del cierre PSUT por producto-anio-grupo, en TJ (1e-6)",
    )
    analizador.add_argument(
        "--tolerancia-emisiones-kt",
        type=decimal_positivo,
        default=Decimal("1e-9"),
        help="tolerancia de identidades y totales de emisiones, en kt (1e-9)",
    )
    return analizador


def ejecutar(argumentos: argparse.Namespace) -> int:
    informe = Informe()
    generados = argumentos.generados.resolve()
    referencias = argumentos.referencias.resolve()

    print("VALIDACION DE LA REPRODUCCION 2018-2024")
    print(f"Directorio generado:   {generados}")
    print(f"Directorio referencia: {referencias}")
    print(
        "Tolerancias: "
        f"campos_abs={argumentos.tolerancia_campos}, "
        f"campos_rel={argumentos.tolerancia_relativa}, "
        f"cierre_psut={argumentos.tolerancia_cierre_tj} TJ, "
        f"emisiones={argumentos.tolerancia_emisiones_kt} kt"
    )
    print()

    encabezado_psut_gen, psut_gen = leer_csv(generados / ARCHIVO_PSUT)
    encabezado_emi_gen, emi_gen = leer_csv(generados / ARCHIVO_EMISIONES)
    encabezado_psut_ref, psut_ref = leer_csv(referencias / ARCHIVO_PSUT)
    encabezado_emi_ref, emi_ref = leer_csv(referencias / ARCHIVO_EMISIONES)

    comparar_archivo(
        "PSUT",
        encabezado_psut_gen,
        psut_gen,
        encabezado_psut_ref,
        psut_ref,
        "registro_mapeo",
        CAMPOS_NUMERICOS_PSUT,
        argumentos.tolerancia_campos,
        argumentos.tolerancia_relativa,
        informe,
    )
    comparar_archivo(
        "Emisiones",
        encabezado_emi_gen,
        emi_gen,
        encabezado_emi_ref,
        emi_ref,
        "clave_emision",
        CAMPOS_NUMERICOS_EMISIONES,
        argumentos.tolerancia_campos,
        argumentos.tolerancia_relativa,
        informe,
    )

    validar_psut(
        "generada",
        encabezado_psut_gen,
        psut_gen,
        argumentos.tolerancia_cierre_tj,
        informe,
    )
    validar_psut(
        "de referencia",
        encabezado_psut_ref,
        psut_ref,
        argumentos.tolerancia_cierre_tj,
        informe,
    )
    totales_generados = validar_emisiones(
        "generadas",
        encabezado_emi_gen,
        emi_gen,
        argumentos.tolerancia_emisiones_kt,
        informe,
    )
    totales_referencia = validar_emisiones(
        "de referencia",
        encabezado_emi_ref,
        emi_ref,
        argumentos.tolerancia_emisiones_kt,
        informe,
    )
    comparar_totales_anuales(
        totales_generados,
        totales_referencia,
        argumentos.tolerancia_emisiones_kt,
        informe,
    )
    if argumentos.modelo_excel is not None:
        validar_gas_natural_excel(
            argumentos.modelo_excel, psut_gen, argumentos.tolerancia_cierre_tj, informe
        )

    print("Totales anuales reproducidos de CO2e (kt):")
    for anio in sorted(ANIOS_ESPERADOS):
        print(f"  {anio}: {totales_generados[anio]}")
    print()
    informe.mostrar()
    return 1 if informe.fallidas else 0


def main() -> int:
    analizador = crear_argumentos()
    argumentos = analizador.parse_args()
    try:
        return ejecutar(argumentos)
    except (FileNotFoundError, OSError, ValueError, csv.Error, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"ERROR DE VALIDACION: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
