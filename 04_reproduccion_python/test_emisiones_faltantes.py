"""Pruebas de factores, procedencia y emisiones cuantificadas (stdlib)."""

from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import reproducir_modelo_guatemala_2018_2024 as modelo
import validar_reproduccion_guatemala_2018_2024 as validador


class EmisionesSinFactor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entrada = modelo.leer_entrada(Path(__file__).with_name(modelo.ARCHIVO_ENTRADA))
        cls.parametros = modelo.obtener_parametros(cls.entrada)
        cls.psut, cls.indice_psut = modelo.construir_psut(cls.entrada, cls.parametros)
        cls.emisiones = modelo.construir_emisiones(cls.entrada, cls.indice_psut, cls.parametros)

    def validar(self, registros):
        informe = validador.Informe()
        totales = validador.validar_emisiones(
            "prueba", validador.COLUMNAS_EMISIONES, registros, Decimal("1e-9"), informe
        )
        return informe, totales

    def fila_petroleo(self, registros):
        return next(f for f in registros if f["modulo"] == "FUGITIVAS" and f["producto_std"] == "PETR")

    def test_n2o_faltante_y_subtotales_fugitivos_se_conservan(self):
        filas = [f for f in self.emisiones if f["modulo"] == "FUGITIVAS" and f["producto_std"] == "PETR"]
        self.assertEqual(len(filas), 7)
        for fila in filas:
            self.assertEqual(fila["ef_n2o_kg_tj"], "")
            self.assertEqual(fila["n2o_kt"], "")
            self.assertIn("CO2e parcial: N2O sin factor numérico", fila["nota"])
        informe, _ = self.validar(self.emisiones)
        self.assertEqual(informe.fallidas, [])
        # El subtotal fugitivo suma los gases cuantificados y conserva N2O vacio.
        esperados = {
            "2018": "0.05145892218", "2019": "0.05268831",
            "2020": "0.04290042", "2021": "0.034625934",
            "2022": "0.019845843", "2023": "0.0274038269165541",
            "2024": "0.0279906871284664",
        }
        for fila in filas:
            self.assertEqual(Decimal(fila["co2e_kt"]), Decimal(esperados[fila["anio"]]))

    def test_ceros_metodologicos_y_filas_sin_gases_permanecen_distintos(self):
        ceros = [f for f in self.emisiones if f["grupo_factor"] == "CERO_DIRECTO"]
        self.assertTrue(ceros)
        for fila in ceros:
            for campo in ("ef_co2_kg_tj", "ef_ch4_kg_tj", "ef_n2o_kg_tj", "co2_directo_kt", "co2_biogenico_memo_kt", "ch4_kt", "n2o_kt", "co2e_kt"):
                self.assertEqual(Decimal(fila[campo]), 0)
        vacias = [f for f in self.emisiones if f["co2e_kt"] == ""]
        self.assertEqual(len(vacias), 41)
        for fila in vacias:
            for campo in ("co2_directo_kt", "co2_biogenico_memo_kt", "ch4_kt", "n2o_kt"):
                self.assertEqual(fila[campo], "")

    def test_faltante_de_otro_gas_tambien_se_preserva(self):
        entrada = [dict(f) for f in self.entrada]
        factor = next(f for f in entrada if f["registro_id"] == "FE_COMB|2018|1.A.4.b|BIOMASS|CH4")
        factor["valor_factor"] = ""
        factor["estado"] = "NO"
        registros = modelo.construir_emisiones(entrada, self.indice_psut, self.parametros)
        fila = next(f for f in registros if f["anio"] == "2018" and f["unidad_sectorial_agregada"] == "HH" and f["producto_std"] == "LENA")
        self.assertEqual(fila["ch4_kt"], "")
        self.assertNotEqual(fila["n2o_kt"], "")
        self.assertNotEqual(fila["co2_biogenico_memo_kt"], "")
        self.assertIn("CO2e parcial: CH4 sin factor numérico", fila["nota"])
        self.assertEqual(self.validar(registros)[0].fallidas, [])

    def test_validador_rechaza_cero_sin_factor_sin_comparar_referencias(self):
        registros = [dict(f) for f in self.emisiones]
        self.fila_petroleo(registros)["n2o_kt"] = "0"
        informe, _ = self.validar(registros)
        self.assertTrue(any("resultados por gas" in f for f in informe.fallidas))
        self.assertTrue(any("7 registros fugitivos" in f for f in informe.fallidas))

    def test_validador_rechaza_subtotal_parcial_sin_nota(self):
        registros = [dict(f) for f in self.emisiones]
        self.fila_petroleo(registros)["nota"] = ""
        self.assertTrue(any("subtotales parciales" in f for f in self.validar(registros)[0].fallidas))

    def test_validador_rechaza_cero_cuando_no_hay_gases_cuantificados(self):
        registros = [dict(f) for f in self.emisiones]
        fila = next(f for f in registros if f["modulo"] == "FUGITIVAS" and f["co2e_kt"] == "")
        fila["co2e_kt"] = "0"
        self.assertTrue(any("presencia del subtotal" in f for f in self.validar(registros)[0].fallidas))

    def test_validador_contrasta_actividad_por_factor_independientemente(self):
        registros = [dict(f) for f in self.emisiones]
        fila = self.fila_petroleo(registros)
        fila["ch4_kt"] = str(Decimal(fila["ch4_kt"]) + 1)
        fila["co2e_kt"] = str(Decimal(fila["co2e_kt"]) + 28)
        # La identidad CO2e sigue cerrando; el control por gas detecta el error.
        informe, _ = self.validar(registros)
        self.assertTrue(any("resultados por gas" in f for f in informe.fallidas))
        self.assertFalse(any("identidad CO2e" in f for f in informe.fallidas))


class ProcedenciaFactores(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = modelo.leer_entrada(Path(__file__).with_name(modelo.ARCHIVO_ENTRADA))
        cls.parametros = modelo.obtener_parametros(cls.original)
        _, cls.psut = modelo.construir_psut(cls.original, cls.parametros)

    def setUp(self):
        self.entrada = [dict(f) for f in self.original]

    def regla(self, producto="GAS", anio="2019"):
        return next(f for f in self.entrada if f["tipo_registro"] == "REGLA_EMISION_ENERGIA"
                    and f["incluir"] == "1" and f["unidad_sectorial"] == "TR_BEN"
                    and f["producto"] == producto and f["anio"] == anio)

    def factores(self, regla):
        return [f for f in self.entrada if f["tipo_registro"] == "FACTOR_EMISION_OBS"
                and f["anio"] == str(min(int(regla["anio"]), 2022))
                and f["categoria_ipcc"] == regla["categoria_ipcc"] and f["grupo_factor"] == regla["grupo_factor"]]

    def construir(self):
        return modelo.construir_emisiones(self.entrada, self.psut, self.parametros)

    def salida_regla(self, filas, regla):
        return next(f for f in filas if f["clave_emision"] == f"EM|{regla['anio']}|{regla['source_record_id']}")

    def validar(self, filas):
        informe = validador.Informe()
        validador.validar_asignacion_factores("prueba", filas, self.entrada, Decimal("1e-9"), informe)
        return informe

    def test_ceros_metodologicos_declaran_su_fuente_real(self):
        filas = self.construir()
        ceros = [f for f in filas if f["grupo_factor"] == "CERO_DIRECTO"]
        self.assertEqual(len(ceros), 79)
        self.assertTrue(all(f["estado_factor"] == "CAL" and f["fuente_id_factor"] == "METODO_EMISIONES" for f in ceros))
        self.assertEqual(self.validar(filas).fallidas, [])

    def test_grupo_por_producto_admite_cardinalidad_distinta(self):
        regla = self.regla("DOIL")
        for factor in self.factores(regla):
            nuevo = dict(factor)
            nuevo.update(grupo_factor="PRUEBA_DOIL", producto="DOIL")
            nuevo["registro_id"] += "|PRUEBA"
            nuevo["clave_union"] = "|".join(nuevo[k] for k in ("anio", "categoria_ipcc", "grupo_factor", "gas"))
            self.entrada.append(nuevo)
        regla["grupo_factor"] = "PRUEBA_DOIL"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / modelo.ARCHIVO_ENTRADA
            with p.open("w", encoding="utf-8", newline="") as f:
                escritor = csv.DictWriter(f, fieldnames=modelo.COLUMNAS_ENTRADA)
                escritor.writeheader()
                escritor.writerows(self.entrada)
            with patch.object(modelo, "CONTEO_FACTORES_ESPERADO", None):
                self.assertEqual(len(modelo.leer_entrada(p)), len(self.original) + 3)
        filas = self.construir()
        self.assertEqual(self.salida_regla(filas, regla)["grupo_factor"], "PRUEBA_DOIL")
        self.assertEqual(self.validar(filas).fallidas, [])

    def test_fuentes_por_gas_se_transmiten_al_compuesto(self):
        regla = self.regla()
        factor = next(f for f in self.factores(regla) if f["gas"] == "CH4")
        factor.update(fuente_id="IPCC_PRUEBA", estado="PRX", fuente_pagina="Tabla de prueba, sin cambio de valor")
        filas = self.construir()
        fila = self.salida_regla(filas, regla)
        self.assertEqual(fila["estado_factor"], "PRX")
        self.assertIn("IPCC_PRUEBA", fila["fuente_id_factor"])
        self.assertIn("CH4: IPCC_PRUEBA [PRX; Tabla de prueba, sin cambio de valor]", fila["nota"])
        compuesto = next(f for f in filas if f["grupo_factor"] == "GAS_COMPUESTO_2019")
        self.assertIn("IPCC_PRUEBA", compuesto["fuente_id_factor"])
        self.assertEqual(self.validar(filas).fallidas, [])
        # Los numeros cierran aun si se falsea el origen; el control de entrada lo detecta.
        fila["fuente_id_factor"] = "FUENTE_INCORRECTA"
        self.assertTrue(self.validar(filas).fallidas)

    def test_estado_cal_heredado_y_prolongacion_se_distinguen(self):
        for anio in ("2019", "2024"):
            regla = self.regla(anio=anio)
            for factor in self.factores(regla):
                factor.update(estado="CAL", fuente_id="CRT_PRUEBA")
        filas = self.construir()
        self.assertEqual(self.salida_regla(filas, self.regla())["estado_factor"], "CAL")
        proyectada = self.salida_regla(filas, self.regla(anio="2024"))
        self.assertEqual(proyectada["estado_factor"], "PRX")
        self.assertEqual(proyectada["anio_factor"], "2022")
        self.assertEqual(self.validar(filas).fallidas, [])
        proyectada["estado_factor"] = "OBS"
        self.assertTrue(self.validar(filas).fallidas)

    def test_gas_ponderado_con_componente_faltante_no_lo_imputa(self):
        factor = next(f for f in self.factores(self.regla()) if f["gas"] == "CH4")
        factor.update(valor_factor="", estado="NO")
        filas = self.construir()
        compuesto = next(f for f in filas if f["grupo_factor"] == "GAS_COMPUESTO_2019")
        self.assertEqual(compuesto["ef_ch4_kg_tj"], "")
        self.assertEqual(compuesto["ch4_kt"], "")
        self.assertNotEqual(compuesto["co2e_kt"], "")
        self.assertIn("CO2e parcial: CH4 sin factor numérico", compuesto["nota"])
        self.assertEqual(self.validar(filas).fallidas, [])

    def test_rechaza_factor_de_otro_producto(self):
        for factor in self.factores(self.regla()):
            factor["producto"] = "PRODUCTO_INCORRECTO"
        with self.assertRaisesRegex(modelo.ErrorModelo, "no corresponde al producto"):
            self.construir()



if __name__ == "__main__":
    unittest.main()
