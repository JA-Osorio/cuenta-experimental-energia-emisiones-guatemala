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
        --referencias ../datasets_finales
"""

from __future__ import annotations

import argparse
import csv
import sys
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


def validar_emisiones(
    etiqueta: str,
    encabezado: Sequence[str],
    registros: Sequence[Mapping[str, str]],
    tolerancia_emisiones: Decimal,
    informe: Informe,
) -> dict[str, Decimal]:
    """Comprueba factores por gas y subtotales de CO2e sin imputar faltantes."""

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
    errores_notas: list[str] = []
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
        presentes = [fila.get(campo, "") != "" for campo in campos_identidad]
        try:
            valores = {
                campo: a_decimal(fila[campo], f"Emisiones/{clave}/{campo}")
                if fila.get(campo, "") != "" else None
                for campo in campos_identidad
            }
            if fila.get("modulo") == "AGRICULTURA":
                # Agricultura incorpora emisiones fuente, no factores kg/TJ.
                if any(presentes) and not all(presentes):
                    errores_presencia.append(clave)
            else:
                factores = {
                    gas: a_decimal(fila[campo], f"Emisiones/{clave}/{campo}")
                    if fila.get(campo, "") != "" else None
                    for gas, campo in (
                        ("CO2", "ef_co2_kg_tj"),
                        ("CH4", "ef_ch4_kg_tj"),
                        ("N2O", "ef_n2o_kg_tj"),
                    )
                }
                disponibles = any(valor is not None for valor in factores.values())
                esperados = {campo: None for campo in campos_identidad[:-1]}
                if disponibles:
                    actividad = a_decimal(fila.get("actividad_emisiones_tj", ""), f"Emisiones/{clave}/actividad")
                    emisiones = {
                        gas: None if factor is None else actividad * factor / Decimal("1000000")
                        for gas, factor in factores.items()
                    }
                    es_biogenico = fila.get("tratamiento_co2") == "BIOGENICO"
                    esperados.update({
                        "co2_directo_kt": Decimal(0) if es_biogenico else emisiones["CO2"],
                        "co2_biogenico_memo_kt": emisiones["CO2"] if es_biogenico else Decimal(0),
                        "ch4_kt": emisiones["CH4"],
                        "n2o_kt": emisiones["N2O"],
                    })
                if (valores["co2e_kt"] is not None) != disponibles:
                    errores_presencia.append(clave)
                for campo, esperado in esperados.items():
                    observado = valores[campo]
                    if ((observado is None) != (esperado is None)
                        or (observado is not None and esperado is not None
                            and abs(observado - esperado) > tolerancia_emisiones)):
                        errores_factores.append(f"{clave}/{campo}: factor y resultado incompatibles")
                if any(valor is not None and valor < 0 for valor in factores.values()):
                    errores_factores.append(f"{clave}: factor negativo")
                if fila.get("grupo_factor") == "CERO_DIRECTO" and (
                    any(valor != Decimal(0) for valor in factores.values())
                    or fila.get("estado_factor") != "CAL"
                ):
                    errores_factores.append(f"{clave}: cero metodologico inconsistente")
                faltantes = [gas for gas, factor in factores.items() if factor is None]
                if disponibles and faltantes:
                    nota_esperada = (
                        "CO2e parcial: " + ", ".join(faltantes)
                        + " sin factor numérico; el total incluye solo los gases cuantificados."
                    )
                    if nota_esperada not in fila.get("nota", ""):
                        errores_notas.append(clave)
        except ValueError as exc:
            if len(errores_numericos) < MAXIMO_EJEMPLOS:
                errores_numericos.append(str(exc))
            continue

        co2e = valores["co2e_kt"]
        if co2e is None:
            continue
        # Suma de componentes conocidos: no se rellena ningun campo ausente.
        # El CO2 biogenico permanece como partida informativa fuera del subtotal.
        co2e_calculado = sum(
            valores[campo] * peso
            for campo, peso in (("co2_directo_kt", Decimal(1)), ("ch4_kt", GWP_CH4), ("n2o_kt", GWP_N2O))
            if valores[campo] is not None
        )
        diferencia = co2e - co2e_calculado
        if abs(diferencia) > tolerancia_emisiones:
            errores_identidad.append((clave, diferencia))
        if anio in totales_co2e:
            totales_co2e[anio] += co2e
            for componente, campo in (
                ("co2_directo", "co2_directo_kt"), ("ch4", "ch4_kt"),
                ("n2o", "n2o_kt"), ("biogenico", "co2_biogenico_memo_kt"),
            ):
                if valores[campo] is not None:
                    totales_componentes[anio][componente] += valores[campo]

    informe.comprobar(
        not errores_presencia,
        f"Emisiones {etiqueta}: presencia del subtotal coherente con los gases disponibles",
        detalle_elementos(errores_presencia),
    )
    informe.comprobar(
        not errores_numericos,
        f"Emisiones {etiqueta}: valores de la identidad validos y finitos",
        "; ".join(errores_numericos),
    )
    informe.comprobar(
        not errores_factores,
        f"Emisiones {etiqueta}: resultados por gas coherentes con actividad y factor; faltantes preservados",
        detalle_elementos(errores_factores),
    )
    informe.comprobar(
        not errores_notas,
        f"Emisiones {etiqueta}: subtotales parciales identifican los gases sin factor",
        detalle_elementos(errores_notas),
    )
    petroleo_fugitivo = [
        fila for fila in registros
        if fila.get("modulo") == "FUGITIVAS" and fila.get("producto_std") == "PETR"
    ]
    informe.comprobar(
        Counter(fila.get("anio") for fila in petroleo_fugitivo)
        == Counter({anio: 1 for anio in ANIOS_ESPERADOS})
        and all(
            fila.get("ef_n2o_kg_tj") == "" and fila.get("n2o_kt") == ""
            and fila.get("co2_directo_kt", "") != "" and fila.get("ch4_kt", "") != ""
            and fila.get("co2e_kt", "") != ""
            for fila in petroleo_fugitivo
        ),
        f"Emisiones {etiqueta}: 7 registros fugitivos de petroleo conservan N2O sin cuantificar",
    )
    errores_identidad.sort(key=lambda elemento: abs(elemento[1]), reverse=True)
    informe.comprobar(
        not errores_identidad,
        f"Emisiones {etiqueta}: identidad CO2e suma gases cuantificados y excluye CO2 biogenico",
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


def validar_asignacion_factores(
    etiqueta: str,
    registros: Sequence[Mapping[str, str]],
    entrada: Sequence[Mapping[str, str]],
    tolerancia: Decimal,
    informe: Informe,
) -> None:
    """Contrasta la salida con reglas y factores fuente, sin importar el generador."""
    errores: list[str] = []
    try:
        reglas = {}
        factores = {}
        for fila in entrada:
            if fila["tipo_registro"] == "REGLA_EMISION_ENERGIA" and fila["incluir"] == "1":
                clave = tuple(fila[c] for c in ("anio", "source_record_id", "lado", "bloque", "unidad_sectorial", "metodo"))
                if clave in reglas:
                    errores.append(f"Regla duplicada: {clave}")
                reglas[clave] = fila
            elif fila["tipo_registro"] == "FACTOR_EMISION_OBS":
                clave = tuple(fila[c] for c in ("anio", "categoria_ipcc", "grupo_factor", "gas"))
                if clave in factores:
                    errores.append(f"Factor duplicado: {clave}")
                factores[clave] = fila

        metadatos = {}
        compuesto = []
        gases_campos = (("CO2", "ef_co2_kg_tj"), ("CH4", "ef_ch4_kg_tj"), ("N2O", "ef_n2o_kg_tj"))

        def contrastar(fila, valores, estado, fuentes, anio_factor):
            identificador = fila["clave_emision"]
            for gas, campo in gases_campos:
                observado = None if fila[campo] == "" else a_decimal(fila[campo], identificador)
                esperado = valores[gas]
                if ((observado is None) != (esperado is None)
                    or (observado is not None and esperado is not None and abs(observado - esperado) > tolerancia)):
                    errores.append(f"{identificador}/{gas}: factor aplicado distinto del insumo")
            if fila["estado_factor"] != estado or fila["fuente_id_factor"] != fuentes or fila["anio_factor"] != str(anio_factor):
                errores.append(f"{identificador}: estado, fuente o año de factor incoherente")

        for fila in registros:
            if fila["modulo"] == "AGRICULTURA":
                continue
            clave = tuple(fila[c] for c in ("anio", "source_record_id", "psut_side", "psut_block_code", "unidad_origen_psut", "metodo_asignacion"))
            regla = reglas[clave]
            for campo_salida, campo_regla in (("categoria_ipcc", "categoria_ipcc"), ("grupo_factor", "grupo_factor"), ("producto_std", "producto"), ("tratamiento_co2", "tratamiento_co2")):
                if fila[campo_salida] != regla[campo_regla]:
                    errores.append(f"{fila['clave_emision']}: correspondencia {campo_salida} distinta de la regla")
            if regla["metodo"] == "USO_ENERGETICO_INTERNO_APARENTE":
                compuesto.append(fila)
                continue
            anio = int(fila["anio"])
            anio_factor = min(anio, 2022)
            fuentes_gas = {gas: factores[(str(anio_factor), regla["categoria_ipcc"], regla["grupo_factor"], gas)] for gas, _ in gases_campos}
            valores = {gas: None if f["valor_factor"] == "" else a_decimal(f["valor_factor"], f["registro_id"]) for gas, f in fuentes_gas.items()}
            for gas, f in fuentes_gas.items():
                if (f["unidad_factor"] != f"kg {gas}/TJ" or not f["fuente_id"] or not f["fuente_pagina"]
                    or f["estado"] not in {"OBS", "CAL", "PRX", "NO"}
                    or (valores[gas] is None) != (f["estado"] == "NO")
                    or (f["producto"] and f["producto"] != regla["producto"])):
                    errores.append(f"{f['registro_id']}: metadatos fuente incompatibles")
            conocidos = [fuentes_gas[gas] for gas, valor in valores.items() if valor is not None]
            fuentes = " | ".join(sorted({f["fuente_id"] for f in (conocidos or list(fuentes_gas.values()))}))
            if not conocidos:
                estado = "NO"
            elif regla["grupo_factor"] == "CERO_DIRECTO":
                estado = "CAL"
                if any(v != Decimal(0) for v in valores.values()) or any(f["estado"] != "CAL" for f in conocidos):
                    errores.append(f"{fila['clave_emision']}: factores de cero metodológico inválidos")
            elif anio > anio_factor or "PRX" in {f["estado"] for f in conocidos}:
                estado = "PRX"
            else:
                estado = "CAL" if "CAL" in {f["estado"] for f in conocidos} else "OBS"
            contrastar(fila, valores, estado, fuentes, anio_factor)
            requiere_detalle = (
                len({f["fuente_id"] for f in conocidos}) > 1
                or any(f["producto"] or f["metodo"] not in {"CRT_ANUAL", "CERO_DIRECTO", "SIN_FACTOR_NUMERICO", "EMISION_CRT_DIV_PSUT_EXTRACCION"}
                       or f["fuente_id"] not in {"UNFCCC_GTM_CRT_2024", "METODO_EMISIONES"} for f in fuentes_gas.values())
            )
            if requiere_detalle:
                for gas, f in fuentes_gas.items():
                    if f"{gas}: {f['fuente_id']} [{f['estado']}; {f['fuente_pagina']}]" not in fila["nota"]:
                        errores.append(f"{fila['clave_emision']}/{gas}: falta procedencia detallada en nota")
            metadatos[fila["clave_emision"]] = (valores, fuentes)

        referencias = [f for f in registros if f["anio"] == "2019" and f["modulo"] == "COMBUSTION" and f["producto_std"] == "GAS" and f["unidad_sectorial_agregada"] in {"IND_BEN", "SERV", "TR_BEN"}]
        if len(compuesto) != 1 or len(referencias) != 3 or {f["unidad_sectorial_agregada"] for f in referencias} != {"IND_BEN", "SERV", "TR_BEN"}:
            errores.append("La ponderación GAS 2019 requiere una fila compuesta y tres sectores de referencia")
        else:
            actividad_total = sum(a_decimal(f["actividad_emisiones_tj"], f["clave_emision"]) for f in referencias)
            if actividad_total <= 0:
                errores.append("La ponderación GAS 2019 no tiene actividad positiva")
            else:
                ponderados = {}
                for gas, _ in gases_campos:
                    pares = [(a_decimal(f["actividad_emisiones_tj"], f["clave_emision"]), metadatos[f["clave_emision"]][0][gas]) for f in referencias]
                    ponderados[gas] = None if any(a != 0 and v is None for a, v in pares) else sum(a * v for a, v in pares if v is not None) / actividad_total
                fuentes = " | ".join(sorted({s for f in referencias for s in metadatos[f["clave_emision"]][1].split(" | ")}))
                estado = "PRX" if any(v is not None for v in ponderados.values()) else "NO"
                contrastar(compuesto[0], ponderados, estado, fuentes, 2019)
    except (KeyError, ValueError, InvalidOperation) as exc:
        errores.append(f"Entrada o correspondencia incompleta: {exc}")
    informe.comprobar(
        not errores,
        f"Emisiones {etiqueta}: factores, fuentes y estados corresponden a la entrada y sus reglas",
        detalle_elementos(errores),
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
        default=directorio_script.parent / "datasets_finales",
        help="directorio que contiene los dos CSV finales de referencia",
    )
    analizador.add_argument(
        "--entrada",
        type=Path,
        help="CSV de entrada para contrastar asignaciones y procedencia; por defecto se busca junto al script",
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
    entrada = argumentos.entrada
    if entrada is None:
        candidata = Path(__file__).resolve().parent / "datos_modelo_guatemala_2018_2024.csv"
        entrada = candidata if candidata.is_file() else None
    if entrada is None:
        print("Sin CSV de entrada: no se valida la asignación de factores, fuentes y estados contra el insumo.")
    else:
        print(f"Entrada para validar asignaciones: {entrada.resolve()}")
        _, filas_entrada = leer_csv(entrada)
        validar_asignacion_factores("generadas", emi_gen, filas_entrada, argumentos.tolerancia_campos, informe)
        validar_asignacion_factores("de referencia", emi_ref, filas_entrada, argumentos.tolerancia_campos, informe)
    comparar_totales_anuales(
        totales_generados,
        totales_referencia,
        argumentos.tolerancia_emisiones_kt,
        informe,
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
    except (FileNotFoundError, OSError, ValueError, csv.Error) as exc:
        print(f"ERROR DE VALIDACION: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
