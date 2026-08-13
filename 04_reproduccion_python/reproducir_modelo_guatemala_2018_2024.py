#!/usr/bin/env python3
"""Cuenta experimental de energía y emisiones al aire de Guatemala, 2018–2024.

Autores:
    Juan Alejandro Osorio
    Patricia Villatoro
    Noe Salguero
    José Carlos Soberanis

Las afiliaciones, los identificadores ORCID y los demás créditos se presentan
en ``creditos.txt``.

El programa utiliza exclusivamente ``datos_modelo_guatemala_2018_2024.csv``
y la biblioteca estándar de Python.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ARCHIVO_ENTRADA = "datos_modelo_guatemala_2018_2024.csv"
ARCHIVO_PSUT = "psut_energia_guatemala_2018_2024.csv"
ARCHIVO_EMISIONES = "cuenta_emisiones_aire_guatemala_2018_2024.csv"
AÑOS = tuple(range(2018, 2025))
METODOS_APARENTES = {
    "USO_NO_ENERGETICO_APARENTE",
    "USO_ENERGETICO_INTERNO_APARENTE",
}
METODO_GAS_NO_ASIGNADO = "USO_ENERGETICO_INTERNO_APARENTE"
FUENTE_GAS_NO_ASIGNADO = "GAS_USO_INTERNO_APARENTE_2019"
GRUPO_GAS_COMPUESTO = "GAS_COMPUESTO_2019"

COLUMNAS_ENTRADA = [
    "tipo_registro", "registro_id", "clave_union", "anio", "anio_fuente",
    "estado", "fuente_id", "titulo_fuente", "url_fuente",
    "source_record_id", "producto", "nombre_producto", "flow_group",
    "lado", "bloque", "unidad_sectorial", "metodo", "ajuste",
    "valor_original", "unidad_original", "valor_tj", "cero_imputado",
    "categoria_ipcc", "categoria_nombre", "grupo_factor", "gas",
    "valor_factor", "unidad_factor", "tratamiento_co2",
    "emision_kt_gas", "valor_vab", "unidad_vab", "parametro",
    "valor_parametro", "unidad_parametro", "incluir", "clave_notacion",
    "fuente_pagina", "nota",
]

COLUMNAS_PSUT = [
    "registro_mapeo", "anio", "producto", "flow_group", "lado", "bloque",
    "unidad_sectorial", "source_record_id", "metodo", "ajuste", "TJ",
    "tipo_STAT", "estado_fuente",
]

COLUMNAS_EMISIONES = [
    "clave_emision", "anio", "unidad_sectorial_agregada", "modulo",
    "categoria_ipcc", "categoria_nombre", "producto_std",
    "metodo_asignacion", "unidad_origen_psut", "psut_side",
    "psut_block_code", "source_record_id", "actividad_base_tj",
    "actividad_emisiones_tj", "grupo_factor", "tratamiento_co2",
    "anio_factor", "estado_factor", "ef_co2_kg_tj", "ef_ch4_kg_tj",
    "ef_n2o_kg_tj", "gas_fuente", "emision_fuente_kt_gas",
    "co2_directo_kt", "co2_biogenico_memo_kt", "ch4_kt", "n2o_kt",
    "co2e_kt", "estado_resultado", "clave_notacion", "metodo_calculo",
    "fuente_id_actividad", "fuente_id_factor", "nota",
]

CONTEOS_ESPERADOS = {
    "BALANCE": 1778,
    "MAPEO_PSUT": 617,
    "REGLA_EMISION_ENERGIA": 617,
    "ACTIVIDAD_REFINACION_OBS": 5,
    "EMISION_AGRICULTURA_OBS": 50,
    "VAB_AGRICULTURA": 7,
    "FACTOR_EMISION_OBS": 330,
    "PARAMETRO": 8,
    "CATALOGO_PRODUCTO": 19,
    "CATALOGO_UNIDAD": 15,
}

ESPECIFICACIONES_AGRICULTURA = [
    ("3.A", "Fermentación entérica", "CH4"),
    ("3.B", "Gestión del estiércol", "CH4"),
    ("3.B", "Gestión del estiércol", "N2O"),
    ("3.C", "Cultivo de arroz", "CH4"),
    ("3.D", "Suelos agrícolas", "N2O"),
    ("3.E", "Quema prescrita de sabanas", "CH4"),
    ("3.E", "Quema prescrita de sabanas", "N2O"),
    ("3.F", "Quema de residuos agrícolas en el campo", "CH4"),
    ("3.F", "Quema de residuos agrícolas en el campo", "N2O"),
    ("3.H", "Aplicación de urea", "CO2"),
    ("3.G", "Encalado", "NO"),
    ("3.I", "Otros fertilizantes que contienen carbono", "NO"),
    ("3.J", "Otros", "NO"),
]


class ErrorModelo(RuntimeError):
    """Indica que los datos no cumplen las condiciones del modelo."""


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise ErrorModelo(mensaje)


def decimal_obligatorio(valor: str, contexto: str) -> Decimal:
    exigir(valor != "", f"Falta un valor numérico en {contexto}.")
    try:
        numero = Decimal(valor)
    except InvalidOperation as exc:
        raise ErrorModelo(f"Valor numérico inválido en {contexto}: {valor!r}.") from exc
    exigir(numero.is_finite(), f"Valor no finito en {contexto}.")
    return numero


def flotante_opcional(valor: str, contexto: str) -> float | None:
    if valor == "":
        return None
    try:
        numero = float(valor)
    except ValueError as exc:
        raise ErrorModelo(f"Valor numérico inválido en {contexto}: {valor!r}.") from exc
    exigir(math.isfinite(numero), f"Valor no finito en {contexto}.")
    return numero


def entero_obligatorio(valor: str, contexto: str) -> int:
    exigir(bool(re.fullmatch(r"-?\d+", valor)), f"Entero inválido en {contexto}: {valor!r}.")
    return int(valor)


def texto_decimal(numero: Decimal) -> str:
    if numero == 0:
        return "0"
    return format(numero, "f").rstrip("0").rstrip(".")


def texto_excel(numero: float | None) -> str:
    """Representa un doble con la precisión numérica usada por la salida tabular."""
    if numero is None:
        return ""
    exigir(math.isfinite(numero), "Se obtuvo un resultado numérico no finito.")
    if numero == 0:
        return "0"
    decimal = Decimal(str(numero))
    with localcontext() as contexto:
        contexto.prec = 50
        escala = Decimal(1).scaleb(decimal.copy_abs().adjusted() - 14)
        redondeado = decimal.quantize(escala, rounding=ROUND_HALF_UP)
    if abs(redondeado) < Decimal("0.0001"):
        exponente = redondeado.copy_abs().adjusted()
        mantisa = redondeado.copy_abs().scaleb(-exponente)
        texto_mantisa = format(mantisa, "f").rstrip("0").rstrip(".")
        signo_numero = "-" if redondeado < 0 else ""
        return f"{signo_numero}{texto_mantisa}E{exponente:+04d}"
    return format(redondeado, "f").rstrip("0").rstrip(".")


def leer_entrada(ruta: Path) -> list[dict[str, str]]:
    exigir(ruta.is_file(), f"No se encontró el archivo de entrada: {ruta}")
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        exigir(lector.fieldnames == COLUMNAS_ENTRADA, "El esquema del archivo de entrada no coincide con el esperado.")
        filas = list(lector)
    exigir(all(None not in fila for fila in filas), "Hay filas con más campos que el encabezado.")
    exigir(len(filas) == sum(CONTEOS_ESPERADOS.values()), "El número total de registros no coincide con el modelo.")
    conteos = Counter(fila["tipo_registro"] for fila in filas)
    exigir(conteos == Counter(CONTEOS_ESPERADOS), f"Los tipos de registro o sus cantidades son inconsistentes: {dict(conteos)}")
    identificadores = [fila["registro_id"] for fila in filas]
    exigir(all(identificadores), "Hay registros sin identificador.")
    exigir(len(identificadores) == len(set(identificadores)), "Hay identificadores de registro duplicados.")
    return filas


def indice_unico(
    filas: Iterable[Mapping[str, str]],
    campos: Sequence[str],
    descripcion: str,
) -> dict[tuple[str, ...], Mapping[str, str]]:
    indice: dict[tuple[str, ...], Mapping[str, str]] = {}
    for fila in filas:
        clave = tuple(fila[campo] for campo in campos)
        exigir(clave not in indice, f"Clave duplicada en {descripcion}: {'|'.join(clave)}")
        indice[clave] = fila
    return indice


def validar_catalogos(filas: Sequence[Mapping[str, str]]) -> None:
    productos = {f["producto"] for f in filas if f["tipo_registro"] == "CATALOGO_PRODUCTO"}
    unidades = {f["unidad_sectorial"] for f in filas if f["tipo_registro"] == "CATALOGO_UNIDAD"}
    exigir("" not in productos and "" not in unidades, "Los catálogos contienen códigos vacíos.")
    exigir(len(productos) == CONTEOS_ESPERADOS["CATALOGO_PRODUCTO"], "Hay productos duplicados en el catálogo.")
    exigir(len(unidades) == CONTEOS_ESPERADOS["CATALOGO_UNIDAD"], "Hay unidades duplicadas en el catálogo.")
    for fila in filas:
        if fila["producto"] and fila["tipo_registro"] not in {"PARAMETRO", "CATALOGO_UNIDAD"}:
            exigir(fila["producto"] in productos, f"Producto no catalogado: {fila['producto']}")
        if fila["unidad_sectorial"]:
            exigir(fila["unidad_sectorial"] in unidades, f"Unidad sectorial no catalogada: {fila['unidad_sectorial']}")


def obtener_parametros(filas: Sequence[Mapping[str, str]]) -> dict[str, Decimal]:
    esperados = {
        "factor_kbep_tj", "redondeo_kbep", "tolerancia_cierre_modelo_tj",
        "kg_por_kt", "gwp_ch4", "gwp_n2o", "tolerancia_qa_psut_tj",
        "tolerancia_qa_emisiones_kt",
    }
    parametros: dict[str, Decimal] = {}
    for fila in filas:
        if fila["tipo_registro"] != "PARAMETRO":
            continue
        nombre = fila["parametro"]
        exigir(nombre not in parametros, f"Parámetro duplicado: {nombre}")
        parametros[nombre] = decimal_obligatorio(fila["valor_parametro"], f"parámetro {nombre}")
    exigir(set(parametros) == esperados, "El conjunto de parámetros es incompleto o contiene nombres inesperados.")
    exigir(parametros["factor_kbep_tj"] > 0, "El factor de conversión debe ser positivo.")
    exigir(parametros["kg_por_kt"] == Decimal("1000000"), "La conversión de kg a kt es inconsistente.")
    exigir(parametros["gwp_ch4"] > 0 and parametros["gwp_n2o"] > 0, "Los potenciales de calentamiento deben ser positivos.")
    return parametros


def construir_psut(
    filas: Sequence[Mapping[str, str]],
    parametros: Mapping[str, Decimal],
) -> tuple[list[dict[str, str]], dict[tuple[str, str, str, str, str, str], float]]:
    balances = [f for f in filas if f["tipo_registro"] == "BALANCE"]
    balance_por_id = indice_unico(balances, ("source_record_id",), "balance energético")
    mapeos = [f for f in filas if f["tipo_registro"] == "MAPEO_PSUT"]
    exigir(len({f["clave_union"] for f in mapeos}) == len(mapeos), "Hay claves de mapeo PSUT duplicadas.")
    factor = parametros["factor_kbep_tj"]
    valores: list[Decimal | None] = []
    valores_calculo: list[float | None] = []

    for mapeo in mapeos:
        año = entero_obligatorio(mapeo["anio"], f"año de {mapeo['registro_id']}")
        exigir(año in AÑOS, f"Año fuera del período en {mapeo['registro_id']}.")
        derivado = mapeo["source_record_id"].startswith("STAT_") or mapeo["metodo"] in METODOS_APARENTES
        if derivado:
            valores.append(None)
            valores_calculo.append(None)
            continue
        clave = (mapeo["source_record_id"],)
        exigir(clave in balance_por_id, f"No existe el balance requerido por {mapeo['registro_id']}.")
        balance = balance_por_id[clave]
        exigir(balance["anio"] == mapeo["anio"], f"El año no coincide en {mapeo['registro_id']}.")
        exigir(balance["producto"] == mapeo["producto"], f"El producto no coincide en {mapeo['registro_id']}.")
        exigir(balance["unidad_original"] == "kBEP", f"Unidad de balance inesperada en {mapeo['registro_id']}.")
        valor = decimal_obligatorio(balance["valor_original"], f"balance {balance['registro_id']}") * factor
        valor_calculo = float(balance["valor_original"]) * float(factor)
        if mapeo["ajuste"] == "cambio de signo":
            valor = -valor
            valor_calculo = -valor_calculo
        elif mapeo["ajuste"] == "valor absoluto":
            valor = abs(valor)
            valor_calculo = abs(valor_calculo)
        else:
            exigir(mapeo["ajuste"] == "sin ajuste", f"Ajuste desconocido en {mapeo['registro_id']}.")
        valores.append(valor)
        valores_calculo.append(valor_calculo)

    def suma_grupo(año: str, producto: str, lado: str, excluir_aparentes: bool) -> Decimal:
        total = Decimal(0)
        for mapeo, valor in zip(mapeos, valores):
            if (
                mapeo["anio"] == año
                and mapeo["producto"] == producto
                and mapeo["flow_group"] == "Energy products"
                and mapeo["lado"] == lado
                and mapeo["unidad_sectorial"] != "STAT"
                and (not excluir_aparentes or mapeo["metodo"] not in METODOS_APARENTES)
            ):
                total += valor or Decimal(0)
        return total

    def suma_grupo_calculo(año: str, producto: str, lado: str, excluir_aparentes: bool) -> float:
        return sum(
            (valor or 0.0)
            for mapeo, valor in zip(mapeos, valores_calculo)
            if (
                mapeo["anio"] == año
                and mapeo["producto"] == producto
                and mapeo["flow_group"] == "Energy products"
                and mapeo["lado"] == lado
                and mapeo["unidad_sectorial"] != "STAT"
                and (not excluir_aparentes or mapeo["metodo"] not in METODOS_APARENTES)
            )
        )

    for indice, mapeo in enumerate(mapeos):
        if mapeo["metodo"] in METODOS_APARENTES:
            oferta = suma_grupo(mapeo["anio"], mapeo["producto"], "Supply", True)
            uso_observado = suma_grupo(mapeo["anio"], mapeo["producto"], "Use", True)
            valores[indice] = oferta - uso_observado
            oferta_calculo = suma_grupo_calculo(mapeo["anio"], mapeo["producto"], "Supply", True)
            uso_calculo = suma_grupo_calculo(mapeo["anio"], mapeo["producto"], "Use", True)
            valores_calculo[indice] = round(oferta_calculo - uso_calculo, 10)

    for indice, mapeo in enumerate(mapeos):
        if mapeo["source_record_id"].startswith("STAT_"):
            oferta = suma_grupo(mapeo["anio"], mapeo["producto"], "Supply", False)
            uso = suma_grupo(mapeo["anio"], mapeo["producto"], "Use", False)
            valores[indice] = oferta - uso
            oferta_calculo = suma_grupo_calculo(mapeo["anio"], mapeo["producto"], "Supply", False)
            uso_calculo = suma_grupo_calculo(mapeo["anio"], mapeo["producto"], "Use", False)
            valores_calculo[indice] = round(oferta_calculo - uso_calculo, 10)

    exigir(all(valor is not None for valor in valores), "No se calcularon todos los flujos PSUT.")
    exigir(all(valor is not None for valor in valores_calculo), "No se prepararon todos los flujos para el cálculo de emisiones.")
    salida: list[dict[str, str]] = []
    busqueda: dict[tuple[str, str, str, str, str, str], float] = {}
    for mapeo, valor_opcional, valor_calculo_opcional in zip(mapeos, valores, valores_calculo):
        valor = valor_opcional if valor_opcional is not None else Decimal(0)
        valor_calculo = valor_calculo_opcional if valor_calculo_opcional is not None else 0.0
        calculado_stat = mapeo["source_record_id"].startswith("STAT_")
        calculado_aparente = mapeo["metodo"] in METODOS_APARENTES
        salida.append({
            "registro_mapeo": mapeo["registro_id"],
            "anio": mapeo["anio"],
            "producto": mapeo["producto"],
            "flow_group": mapeo["flow_group"],
            "lado": mapeo["lado"],
            "bloque": mapeo["bloque"],
            "unidad_sectorial": mapeo["unidad_sectorial"],
            "source_record_id": mapeo["source_record_id"],
            "metodo": mapeo["metodo"],
            "ajuste": mapeo["ajuste"],
            "TJ": texto_decimal(valor),
            "tipo_STAT": "redondeo" if calculado_stat else "",
            "estado_fuente": "FORMULA" if calculado_stat else ("CAL" if calculado_aparente else "OK"),
        })
        clave = (
            mapeo["anio"], mapeo["source_record_id"], mapeo["lado"],
            mapeo["bloque"], mapeo["unidad_sectorial"], mapeo["metodo"],
        )
        exigir(clave not in busqueda, f"Clave PSUT ambigua: {'|'.join(clave)}")
        busqueda[clave] = valor_calculo

    exigir(len(salida) == 617, "La PSUT no contiene 617 registros.")
    exigir(sum(f["metodo"] == "USO_NO_ENERGETICO_APARENTE" for f in salida) == 7, "Faltan usos no energéticos aparentes.")
    exigir(sum(f["metodo"] == METODO_GAS_NO_ASIGNADO for f in salida) == 1, "El uso de gas no asignado no es único.")
    tolerancia = parametros["tolerancia_cierre_modelo_tj"]
    saldos: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for mapeo, valor_opcional in zip(mapeos, valores):
        if mapeo["flow_group"] != "Energy products":
            continue
        signo = Decimal(1) if mapeo["lado"] == "Supply" else Decimal(-1)
        saldos[(mapeo["anio"], mapeo["producto"])] += signo * (valor_opcional or Decimal(0))
    abiertos = {clave: saldo for clave, saldo in saldos.items() if abs(saldo) > tolerancia}
    exigir(not abiertos, f"La PSUT no cierra dentro de la tolerancia: {abiertos}")
    return salida, busqueda


def construir_emisiones(
    filas: Sequence[Mapping[str, str]],
    psut: Mapping[tuple[str, str, str, str, str, str], float],
    parametros: Mapping[str, Decimal],
) -> list[dict[str, str]]:
    reglas = [
        f for f in filas
        if f["tipo_registro"] == "REGLA_EMISION_ENERGIA" and f["incluir"] == "1"
    ]
    exigir(len(reglas) == 283, "El número de reglas energéticas incluidas no coincide.")
    for fila in filas:
        if fila["tipo_registro"] == "REGLA_EMISION_ENERGIA":
            exigir(fila["incluir"] in {"0", "1"}, f"Indicador de inclusión inválido en {fila['registro_id']}.")

    factores_filas = [f for f in filas if f["tipo_registro"] == "FACTOR_EMISION_OBS"]
    factores = indice_unico(
        factores_filas, ("anio", "categoria_ipcc", "grupo_factor", "gas"),
        "factores de emisión",
    )
    exigir({f["gas"] for f in factores_filas} == {"CO2", "CH4", "N2O"}, "El conjunto de gases de los factores es inconsistente.")
    exigir({entero_obligatorio(f["anio"], f"factor {f['registro_id']}") for f in factores_filas} == set(range(2018, 2023)), "Los años de los factores son incompletos.")

    observaciones_refinacion = {
        entero_obligatorio(f["anio"], f"actividad {f['registro_id']}"): flotante_opcional(f["valor_tj"], f"actividad {f['registro_id']}")
        for f in filas if f["tipo_registro"] == "ACTIVIDAD_REFINACION_OBS"
    }
    exigir(set(observaciones_refinacion) == set(range(2018, 2023)), "Las actividades observadas de refinación son incompletas.")
    reglas_refinacion = {entero_obligatorio(f["anio"], f"regla {f['registro_id']}"): f for f in reglas if f["metodo"] == "TRANSFORMACION_REFINERIA"}
    exigir(set(reglas_refinacion) == set(AÑOS), "Debe existir una regla anual de refinación.")
    coeficientes: dict[int, float] = {}
    for año in range(2018, 2023):
        regla = reglas_refinacion[año]
        clave = (regla["anio"], regla["source_record_id"], regla["lado"], regla["bloque"], regla["unidad_sectorial"], regla["metodo"])
        exigir(clave in psut and psut[clave] != 0, f"No se puede derivar el coeficiente de refinación de {año}.")
        observado = observaciones_refinacion[año]
        exigir(observado is not None and observado >= 0, f"Actividad de refinación inválida en {año}.")
        coeficientes[año] = observado / psut[clave]
    coeficientes[2023] = coeficientes[2022]
    coeficientes[2024] = coeficientes[2022]

    gwp_ch4 = float(parametros["gwp_ch4"])
    gwp_n2o = float(parametros["gwp_n2o"])
    kg_por_kt = float(parametros["kg_por_kt"])
    calculos: list[dict[str, object]] = []

    reglas_ordenadas = sorted(
        reglas,
        key=lambda f: (
            entero_obligatorio(f["anio"], f"regla {f['registro_id']}"),
            f["categoria_ipcc"], f["unidad_sectorial"], f["source_record_id"],
        ),
    )
    for regla in reglas_ordenadas:
        año = entero_obligatorio(regla["anio"], f"regla {regla['registro_id']}")
        exigir(año in AÑOS, f"Año fuera del período en {regla['registro_id']}.")
        clave_psut = (
            regla["anio"], regla["source_record_id"], regla["lado"],
            regla["bloque"], regla["unidad_sectorial"], regla["metodo"],
        )
        exigir(clave_psut in psut, f"No existe la actividad PSUT de {regla['registro_id']}.")
        base = psut[clave_psut]
        if regla["metodo"] == "TRANSFORMACION_REFINERIA":
            actividad = base * coeficientes[año]
        else:
            actividad = base

        if regla["metodo"] == METODO_GAS_NO_ASIGNADO:
            exigir(regla["source_record_id"] == FUENTE_GAS_NO_ASIGNADO, "La regla del gas no asignado tiene una fuente inesperada.")
            continue

        año_factor = min(año, 2022)
        valores_factor: dict[str, float | None] = {}
        for gas in ("CO2", "CH4", "N2O"):
            clave_factor = (str(año_factor), regla["categoria_ipcc"], regla["grupo_factor"], gas)
            exigir(clave_factor in factores, f"Falta el factor {'|'.join(clave_factor)}.")
            fila_factor = factores[clave_factor]
            unidad_esperada = f"kg {gas}/TJ"
            exigir(fila_factor["unidad_factor"] == unidad_esperada, f"Unidad de factor inconsistente en {'|'.join(clave_factor)}.")
            valores_factor[gas] = flotante_opcional(fila_factor["valor_factor"], f"factor {'|'.join(clave_factor)}")
            exigir(
                valores_factor[gas] is None or valores_factor[gas] >= 0,
                f"El factor {'|'.join(clave_factor)} no puede ser negativo.",
            )

        disponible = any(valor is not None for valor in valores_factor.values())
        if disponible:
            ef_co2 = valores_factor["CO2"] or 0.0
            ef_ch4 = valores_factor["CH4"] or 0.0
            ef_n2o = valores_factor["N2O"] or 0.0
            co2 = 0.0 if regla["tratamiento_co2"] == "BIOGENICO" else actividad * ef_co2 / kg_por_kt
            biogenico = actividad * ef_co2 / kg_por_kt if regla["tratamiento_co2"] == "BIOGENICO" else 0.0
            ch4 = actividad * ef_ch4 / kg_por_kt
            n2o = actividad * ef_n2o / kg_por_kt
            co2e = co2 + ch4 * gwp_ch4 + n2o * gwp_n2o
        else:
            co2 = biogenico = ch4 = n2o = co2e = None
        estado_factor = "NO" if not disponible else (
            "CAL" if regla["grupo_factor"] == "CERO_DIRECTO" else ("OBS" if año <= 2022 else "PRX")
        )
        calculos.append({
            "clave_emision": f"EM|{año}|{regla['source_record_id']}",
            "anio": año,
            "unidad": "B" if regla["categoria_ipcc"].startswith("1.B") else regla["unidad_sectorial"],
            "modulo": "FUGITIVAS" if regla["categoria_ipcc"].startswith("1.B") else "COMBUSTION",
            "categoria": regla["categoria_ipcc"],
            "nombre": regla["categoria_nombre"],
            "producto": regla["producto"],
            "metodo": regla["metodo"],
            "unidad_origen": regla["unidad_sectorial"],
            "lado": regla["lado"],
            "bloque": regla["bloque"],
            "source_record_id": regla["source_record_id"],
            "base": base,
            "actividad": actividad,
            "grupo": regla["grupo_factor"],
            "tratamiento": regla["tratamiento_co2"],
            "anio_factor": año_factor,
            "estado_factor": estado_factor,
            "ef_co2": valores_factor["CO2"],
            "ef_ch4": valores_factor["CH4"],
            "ef_n2o": valores_factor["N2O"],
            "gas_fuente": None,
            "emision_fuente": None,
            "co2": co2,
            "biogenico": biogenico,
            "ch4": ch4,
            "n2o": n2o,
            "co2e": co2e,
            "estado_resultado": "CAL" if disponible else "NO",
            "clave_notacion": regla["clave_notacion"],
            "metodo_calculo": "SIN_CALCULO_NO" if not disponible else (
                "CERO_DIRECTO" if regla["grupo_factor"] == "CERO_DIRECTO" else "ACTIVIDAD_X_FE"
            ),
            "fuente_actividad": "MEM_BEN",
            "fuente_factor": "UNFCCC_GTM_CRT_2024",
            "nota": "",
        })

    referencias_gas = [
        c for c in calculos
        if c["anio"] == 2019
        and c["modulo"] == "COMBUSTION"
        and c["producto"] == "GAS"
        and c["unidad"] in {"IND_BEN", "SERV", "TR_BEN"}
    ]
    referencias_gas.sort(key=lambda c: str(c["unidad"]))
    exigir(len(referencias_gas) == 3 and {c["unidad"] for c in referencias_gas} == {"IND_BEN", "SERV", "TR_BEN"}, "No se pueden ponderar los factores del gas no asignado.")
    total_actividad_gas = sum(float(c["actividad"]) for c in referencias_gas)
    exigir(total_actividad_gas > 0, "La actividad de referencia del gas debe ser positiva.")
    factores_compuestos = {
        gas: sum(float(c["actividad"]) * float(c[f"ef_{gas}"]) for c in referencias_gas) / total_actividad_gas
        for gas in ("co2", "ch4", "n2o")
    }
    regla_gas = next((f for f in reglas if f["metodo"] == METODO_GAS_NO_ASIGNADO), None)
    exigir(regla_gas is not None, "Falta la regla del gas no asignado.")
    clave_gas = (
        regla_gas["anio"], regla_gas["source_record_id"], regla_gas["lado"],
        regla_gas["bloque"], regla_gas["unidad_sectorial"], regla_gas["metodo"],
    )
    actividad_gas = psut[clave_gas]
    emisiones_gas = {gas: actividad_gas * factor / kg_por_kt for gas, factor in factores_compuestos.items()}
    co2e_gas = emisiones_gas["co2"] + emisiones_gas["ch4"] * gwp_ch4 + emisiones_gas["n2o"] * gwp_n2o
    calculos.append({
        "clave_emision": "EM|2019|GAS_USO_INTERNO_APARENTE_2019",
        "anio": 2019,
        "unidad": "NO_ASIG",
        "modulo": "COMBUSTION",
        "categoria": "",
        "nombre": "Combustión sin asignación sectorial",
        "producto": "GAS",
        "metodo": METODO_GAS_NO_ASIGNADO,
        "unidad_origen": "NO_ASIG",
        "lado": "Use",
        "bloque": "E",
        "source_record_id": FUENTE_GAS_NO_ASIGNADO,
        "base": actividad_gas,
        "actividad": actividad_gas,
        "grupo": GRUPO_GAS_COMPUESTO,
        "tratamiento": "FOSIL",
        "anio_factor": 2019,
        "estado_factor": "PRX",
        "ef_co2": factores_compuestos["co2"],
        "ef_ch4": factores_compuestos["ch4"],
        "ef_n2o": factores_compuestos["n2o"],
        "gas_fuente": None,
        "emision_fuente": None,
        "co2": emisiones_gas["co2"],
        "biogenico": 0.0,
        "ch4": emisiones_gas["ch4"],
        "n2o": emisiones_gas["n2o"],
        "co2e": co2e_gas,
        "estado_resultado": "PRX",
        "clave_notacion": "",
        "metodo_calculo": "ACTIVIDAD_X_FE_PONDERADO_USOS_OBSERVADOS_2019",
        "fuente_actividad": "MEM_BEN",
        "fuente_factor": "UNFCCC_GTM_CRT_2024",
        "nota": "Factor ponderado por los usos observados de GAS en transporte, industria y servicios.",
    })

    emisiones_observadas_filas = [f for f in filas if f["tipo_registro"] == "EMISION_AGRICULTURA_OBS"]
    emisiones_observadas = indice_unico(
        emisiones_observadas_filas, ("anio", "categoria_ipcc", "gas"),
        "emisiones agrícolas observadas",
    )
    vab_filas = [f for f in filas if f["tipo_registro"] == "VAB_AGRICULTURA"]
    vab = {
        entero_obligatorio(f["anio"], f"VAB {f['registro_id']}"): flotante_opcional(f["valor_vab"], f"VAB {f['registro_id']}")
        for f in vab_filas
    }
    exigir(set(vab) == set(AÑOS) and all(valor is not None and valor > 0 for valor in vab.values()), "La serie de VAB agrícola es incompleta o inválida.")

    def observado_agricultura(año: int, categoria: str, gas: str) -> float | None:
        if gas == "NO":
            return None
        if categoria == "3.F":
            clave_total = (str(año), "3", gas)
            exigir(clave_total in emisiones_observadas, f"Falta el total agrícola {año}|{gas}.")
            valor = flotante_opcional(emisiones_observadas[clave_total]["emision_kt_gas"], f"total agrícola {año}|{gas}")
            exigir(valor is not None, f"El total agrícola {año}|{gas} está vacío.")
            componentes: list[float] = []
            for componente in ("3.A", "3.B", "3.C", "3.D", "3.E"):
                clave_componente = (str(año), componente, gas)
                if clave_componente not in emisiones_observadas:
                    continue
                componente_valor = flotante_opcional(
                    emisiones_observadas[clave_componente]["emision_kt_gas"],
                    f"componente {año}|{componente}|{gas}",
                )
                componentes.append(componente_valor or 0.0)
            return valor - sum(componentes)
        categoria_fuente = "3" if categoria == "3.H" else categoria
        clave = (str(año), categoria_fuente, gas)
        exigir(clave in emisiones_observadas, f"Falta la emisión agrícola {'|'.join(clave)}.")
        return flotante_opcional(emisiones_observadas[clave]["emision_kt_gas"], f"emisión agrícola {'|'.join(clave)}")

    valores_2022 = {
        (categoria, gas): observado_agricultura(2022, categoria, gas)
        for categoria, _, gas in ESPECIFICACIONES_AGRICULTURA
    }
    for año in AÑOS:
        for categoria, nombre, gas in ESPECIFICACIONES_AGRICULTURA:
            if año <= 2022:
                valor = observado_agricultura(año, categoria, gas)
            else:
                base_2022 = valores_2022[(categoria, gas)]
                valor = None if base_2022 is None else base_2022 * float(vab[año]) / float(vab[2022])
            co2 = valor if gas == "CO2" else (0.0 if valor is not None else None)
            biogenico = 0.0 if valor is not None else None
            ch4 = valor if gas == "CH4" else (0.0 if valor is not None else None)
            n2o = valor if gas == "N2O" else (0.0 if valor is not None else None)
            co2e = None if valor is None else co2 + ch4 * gwp_ch4 + n2o * gwp_n2o
            estado = "NO" if valor is None else ("PRX" if año > 2022 else ("CAL" if categoria == "3.F" else "OBS"))
            metodo_calculo = "SIN_CALCULO_NO" if valor is None else (
                "EMISION_2022_X_RATIO_VAB" if año > 2022 else (
                    "TOTAL_SECTOR_MENOS_COMPONENTES" if categoria == "3.F" else "EMISION_OBSERVADA_CRT"
                )
            )
            calculos.append({
                "clave_emision": f"EM|{año}|AGR|{categoria}|{gas}",
                "anio": año,
                "unidad": "A",
                "modulo": "AGRICULTURA",
                "categoria": categoria,
                "nombre": nombre,
                "producto": "",
                "metodo": "PROXY_VAB_DESDE_2022" if año > 2022 and valor is not None else metodo_calculo,
                "unidad_origen": "A",
                "lado": "",
                "bloque": "",
                "source_record_id": f"AGR|{año}|{categoria}|{gas}",
                "base": None,
                "actividad": None,
                "grupo": "NO" if valor is None else "AGRICULTURA_CRT",
                "tratamiento": "FOSIL" if gas == "CO2" else "NO_APLICA",
                "anio_factor": min(año, 2022),
                "estado_factor": estado,
                "ef_co2": None,
                "ef_ch4": None,
                "ef_n2o": None,
                "gas_fuente": gas,
                "emision_fuente": valor,
                "co2": co2,
                "biogenico": biogenico,
                "ch4": ch4,
                "n2o": n2o,
                "co2e": co2e,
                "estado_resultado": estado,
                "clave_notacion": "NO" if valor is None else "",
                "metodo_calculo": metodo_calculo,
                "fuente_actividad": "BANGUAT_SCN_2013" if año > 2022 else "UNFCCC_GTM_CRT_2024",
                "fuente_factor": "" if valor is None else "UNFCCC_GTM_CRT_2024",
                "nota": "",
            })

    calculos.sort(key=lambda c: (int(c["anio"]), 1 if c["modulo"] == "AGRICULTURA" else 0, str(c["unidad"]), str(c["clave_emision"])))
    exigir(len(calculos) == 374, "La cuenta de emisiones no contiene 374 registros.")
    claves = [str(c["clave_emision"]) for c in calculos]
    exigir(len(claves) == len(set(claves)), "Hay claves de emisiones duplicadas.")

    salida: list[dict[str, str]] = []
    for c in calculos:
        salida.append({
            "clave_emision": str(c["clave_emision"]),
            "anio": str(c["anio"]),
            "unidad_sectorial_agregada": str(c["unidad"]),
            "modulo": str(c["modulo"]),
            "categoria_ipcc": str(c["categoria"]),
            "categoria_nombre": str(c["nombre"]),
            "producto_std": str(c["producto"]),
            "metodo_asignacion": str(c["metodo"]),
            "unidad_origen_psut": str(c["unidad_origen"]),
            "psut_side": str(c["lado"]),
            "psut_block_code": str(c["bloque"]),
            "source_record_id": str(c["source_record_id"]),
            "actividad_base_tj": texto_excel(c["base"]),
            "actividad_emisiones_tj": texto_excel(c["actividad"]),
            "grupo_factor": str(c["grupo"]),
            "tratamiento_co2": str(c["tratamiento"]),
            "anio_factor": str(c["anio_factor"]),
            "estado_factor": str(c["estado_factor"]),
            "ef_co2_kg_tj": texto_excel(c["ef_co2"]),
            "ef_ch4_kg_tj": texto_excel(c["ef_ch4"]),
            "ef_n2o_kg_tj": texto_excel(c["ef_n2o"]),
            "gas_fuente": "" if c["gas_fuente"] is None else str(c["gas_fuente"]),
            "emision_fuente_kt_gas": texto_excel(c["emision_fuente"]),
            "co2_directo_kt": texto_excel(c["co2"]),
            "co2_biogenico_memo_kt": texto_excel(c["biogenico"]),
            "ch4_kt": texto_excel(c["ch4"]),
            "n2o_kt": texto_excel(c["n2o"]),
            "co2e_kt": texto_excel(c["co2e"]),
            "estado_resultado": str(c["estado_resultado"]),
            "clave_notacion": str(c["clave_notacion"]),
            "metodo_calculo": str(c["metodo_calculo"]),
            "fuente_id_actividad": str(c["fuente_actividad"]),
            "fuente_id_factor": str(c["fuente_factor"]),
            "nota": str(c["nota"]),
        })

    tolerancia = float(parametros["tolerancia_qa_emisiones_kt"])
    for fila in salida:
        if fila["co2e_kt"] == "":
            continue
        co2 = float(fila["co2_directo_kt"])
        ch4 = float(fila["ch4_kt"])
        n2o = float(fila["n2o_kt"])
        co2e = float(fila["co2e_kt"])
        diferencia = abs(co2 + ch4 * gwp_ch4 + n2o * gwp_n2o - co2e)
        exigir(diferencia <= max(tolerancia, 5e-9), f"La identidad de CO2e no se cumple en {fila['clave_emision']}.")
    return salida


def escribir_csv_atomico(
    ruta: Path,
    columnas: Sequence[str],
    filas: Sequence[Mapping[str, str]],
) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, nombre_temporal = tempfile.mkstemp(prefix=f".{ruta.name}.", suffix=".tmp", dir=ruta.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=columnas, lineterminator="\n")
            escritor.writeheader()
            escritor.writerows(filas)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(nombre_temporal, ruta)
    except Exception:
        try:
            os.unlink(nombre_temporal)
        except FileNotFoundError:
            pass
        raise


def sha256(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def localizar_entrada(argumento: str | None) -> Path:
    if argumento:
        return Path(argumento).expanduser().resolve()
    junto_al_programa = Path(__file__).resolve().parent / ARCHIVO_ENTRADA
    directorio_actual = Path.cwd() / ARCHIVO_ENTRADA
    for candidata in (junto_al_programa, directorio_actual):
        if candidata.is_file():
            return candidata.resolve()
    raise ErrorModelo(
        f"No se encontró {ARCHIVO_ENTRADA} junto al programa ni en el directorio actual."
    )


def argumentos_cli() -> argparse.Namespace:
    analizador = argparse.ArgumentParser(
        description="Reproduce la Cuenta experimental de energía y emisiones al aire de Guatemala, 2018–2024."
    )
    analizador.add_argument("--entrada", help=f"Ruta de {ARCHIVO_ENTRADA}.")
    analizador.add_argument("--salida", help="Directorio donde se escribirán los dos CSV resultantes.")
    return analizador.parse_args()


def ejecutar() -> int:
    opciones = argumentos_cli()
    entrada = localizar_entrada(opciones.entrada)
    salida = Path(opciones.salida).expanduser().resolve() if opciones.salida else entrada.parent
    exigir(not salida.exists() or salida.is_dir(), "La ruta de salida existe y no es un directorio.")

    filas = leer_entrada(entrada)
    validar_catalogos(filas)
    parametros = obtener_parametros(filas)
    filas_psut, indice_psut = construir_psut(filas, parametros)
    filas_emisiones = construir_emisiones(filas, indice_psut, parametros)

    ruta_psut = salida / ARCHIVO_PSUT
    ruta_emisiones = salida / ARCHIVO_EMISIONES
    escribir_csv_atomico(ruta_psut, COLUMNAS_PSUT, filas_psut)
    escribir_csv_atomico(ruta_emisiones, COLUMNAS_EMISIONES, filas_emisiones)

    print(f"Entrada validada: {len(filas)} registros")
    print(f"PSUT: {len(filas_psut)} registros | SHA-256 {sha256(ruta_psut)}")
    print(f"Emisiones: {len(filas_emisiones)} registros | SHA-256 {sha256(ruta_emisiones)}")
    print(f"Directorio de salida: {salida}")
    return 0


def main() -> int:
    try:
        return ejecutar()
    except ErrorModelo as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
