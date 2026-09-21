"""Regresiones de gases sin factor y subtotales cuantificados (stdlib)."""

from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path

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

    def test_n2o_faltante_y_totales_conocidos_se_conservan(self):
        filas = [f for f in self.emisiones if f["modulo"] == "FUGITIVAS" and f["producto_std"] == "PETR"]
        self.assertEqual(len(filas), 7)
        for fila in filas:
            self.assertEqual(fila["ef_n2o_kg_tj"], "")
            self.assertEqual(fila["n2o_kt"], "")
            self.assertIn("CO2e parcial: N2O sin factor numérico", fila["nota"])
        informe, totales = self.validar(self.emisiones)
        self.assertEqual(informe.fallidas, [])
        # Totales publicados antes de la correccion: no se inventa una emision
        # para el gas faltante ni se eliminan los componentes ya cuantificados.
        esperados = {
            "2018": "28612.8775533491103703", "2019": "29730.9837653986777413",
            "2020": "27015.6898353379709203", "2021": "29978.964673262586197",
            "2022": "28320.984684088714227", "2023": "30852.2910573021204321",
            "2024": "33159.6071488938766144",
        }
        for anio, esperado in esperados.items():
            self.assertLessEqual(abs(totales[anio] - Decimal(esperado)), Decimal("1e-9"))

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

    def test_validador_rechaza_el_cero_original_sin_comparar_referencias(self):
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


if __name__ == "__main__":
    unittest.main()
