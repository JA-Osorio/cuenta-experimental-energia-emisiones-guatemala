"""Auditoría de lectura de factores 2018–2022 contra XLSX originales CRT V0.3.

No modifica el ZIP, los XLSX fuente ni los archivos del repositorio.
"""
import csv
import argparse
import hashlib
import io
import json
import math
import posixpath
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL_ATTR = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
MAPPING = {
    ('1.A.1.a.i', 'LIQUID_FUELS'): ('Table1.A(a)s1', 32, 31, 'Liquid fuels'),
    ('1.A.1.a.i', 'SOLID_FUELS'): ('Table1.A(a)s1', 33, 31, 'Solid fuels'),
    ('1.A.1.a.i', 'GASEOUS_FUELS'): ('Table1.A(a)s1', 34, 31, 'Gaseous fuels (6)'),
    ('1.A.1.a.i', 'BIOMASS'): ('Table1.A(a)s1', 37, 31, 'Biomass (3)'),
    ('1.A.1.b', 'LIQUID_FUELS'): ('Table1.A(a)s1', 39, 38, 'Liquid fuels'),
    ('1.A.2', 'AGREGADO_FOSIL'): ('Table1.A(a)s2', 11, 10, 'Liquid fuels'),
    ('1.A.3', 'AGREGADO_FOSIL'): ('Table1.A(a)s3', 11, 10, 'Liquid fuels'),
    ('1.A.4.a', 'LIQUID_FUELS'): ('Table1.A(a)s4', 18, 17, 'Liquid fuels'),
    ('1.A.4.a', 'BIOMASS'): ('Table1.A(a)s4', 23, 17, 'Biomass (3)'),
    ('1.A.4.b', 'LIQUID_FUELS'): ('Table1.A(a)s4', 25, 24, 'Liquid fuels'),
    ('1.A.4.b', 'BIOMASS'): ('Table1.A(a)s4', 30, 24, 'Biomass (3)'),
}
GAS_COLUMNS = {'CO2': ('H', 'E'), 'CH4': ('I', 'F'), 'N2O': ('J', 'G')}


class RawXlsx:
    """Read source OOXML values, cached formulas, comments and merge ranges."""
    def __init__(self, data):
        self.z = zipfile.ZipFile(io.BytesIO(data))
        self.ss = []
        if 'xl/sharedStrings.xml' in self.z.namelist():
            self.ss = [''.join(x.itertext()) for x in ET.fromstring(self.z.read('xl/sharedStrings.xml'))]
        workbook = ET.fromstring(self.z.read('xl/workbook.xml'))
        rels = ET.fromstring(self.z.read('xl/_rels/workbook.xml.rels'))
        targets = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        self.paths, self.cache, self.metadata = {}, {}, {}
        for s in workbook.findall('.//s:sheet', NS):
            target = targets[s.attrib[REL_ATTR]]
            self.paths[s.attrib['name']] = target.lstrip('/') if target.startswith('/') else 'xl/' + target

    def sheet(self, name):
        if name in self.cache:
            return self.cache[name]
        path = self.paths[name]
        tree = ET.fromstring(self.z.read(path))
        cells = {}
        for c in tree.findall('.//s:c', NS):
            v, f = c.find('s:v', NS), c.find('s:f', NS)
            raw = v.text if v is not None else None
            kind = c.attrib.get('t', 'n')
            value = None
            if raw is not None:
                value = self.ss[int(raw)] if kind == 's' else raw if kind in ('str', 'e') else float(raw)
            elif kind == 'inlineStr':
                value = ''.join(c.find('s:is', NS).itertext())
            cells[c.attrib['r']] = {'value': value, 'raw_v': raw,
                'formula': f.text if f is not None else None,
                'xml': ET.tostring(c, encoding='unicode'), 'type': kind}
        relpath = posixpath.join(posixpath.dirname(path), '_rels', posixpath.basename(path) + '.rels')
        comments = {}
        if relpath in self.z.namelist():
            for rel in ET.fromstring(self.z.read(relpath)):
                if rel.attrib.get('Type', '').endswith('/comments'):
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(path), rel.attrib['Target']))
                    for c in ET.fromstring(self.z.read(target)).findall('.//s:comment', NS):
                        comments[c.attrib['ref']] = ''.join(c.itertext())
        self.cache[name] = cells
        self.metadata[name] = {'xml_path': path,
            'merged_ranges': [m.attrib['ref'] for m in tree.findall('.//s:mergeCell', NS)],
            'comments': comments}
        return cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crt-zip', '--zip-crt', dest='zip_crt', required=True, type=Path, help='ZIP original de las CRT V0.3.')
    parser.add_argument('--entrada', '--datos-modelo', dest='entrada', required=True, type=Path, help='Directorio raíz del repositorio, o CSV datos_modelo_guatemala_2018_2024.csv.')
    parser.add_argument('--psut', type=Path, help='CSV PSUT de resultados. Si se omite se toma del repositorio de entrada.')
    parser.add_argument('--salida', '--salida-dir', dest='salida', required=True, type=Path, help='Directorio distinto de las fuentes para evidencia de lectura.')
    args = parser.parse_args()
    ZIP, OUT = args.zip_crt, args.salida
    MODEL = args.entrada / '04_reproduccion_python/datos_modelo_guatemala_2018_2024.csv' if args.entrada.is_dir() else args.entrada
    PSUT = args.psut if args.psut is not None else MODEL.parent.parent / '02_resultados_y_diccionario/psut_energia_guatemala_2018_2024.csv'
    OUT.mkdir(parents=True, exist_ok=True)
    with MODEL.open(encoding='utf-8-sig') as f:
        model_rows = list(csv.DictReader(f))
        target = [r for r in model_rows
                  if r['tipo_registro'] == 'FACTOR_EMISION_OBS'
                  and (r['categoria_ipcc'], r['grupo_factor']) in MAPPING
                  and r['valor_factor'] and float(r['valor_factor']) > 0]
        fugitive_targets = [r for r in model_rows if r['tipo_registro'] == 'FACTOR_EMISION_OBS'
                            and r['categoria_ipcc'] == '1.B.2.a.ii']
    with PSUT.open(encoding='utf-8-sig') as f:
        psut_rows = list(csv.DictReader(f))
    source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ZIP, MODEL, PSUT]}
    expected_positive_ids = {r['registro_id'] for r in model_rows if r['tipo_registro'] == 'FACTOR_EMISION_OBS'
                             and r['valor_factor'] and float(r['valor_factor']) > 0}
    report, transport_details, all_cells, manifest = [], [], {}, []
    transport_checks, transport_raw, missing_n2o = [], {}, []
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None, 'ZIP CRC failure'
        for year in range(2018, 2023):
            filename = f'GTM-CRT-2024-V0.3-{year}-20250304-084824_started.xlsx'
            binary = z.read(filename)
            sha = hashlib.sha256(binary).hexdigest()
            manifest.append({'anio': year, 'archivo': filename, 'sha256': sha,
                             'bytes': len(binary)})
            wb = RawXlsx(binary)
            source = {}
            for sheet_name in sorted({v[0] for v in MAPPING.values()} | {'Table1.D', 'Table1', 'Table1.B.2'}):
                source[sheet_name] = {key: c['value'] for key, c in wb.sheet(sheet_name).items()
                                      if c['value'] is not None}
            all_cells[str(year)] = source
            for r in [t for t in target if int(t['anio']) == year]:
                category, group, gas = r['categoria_ipcc'], r['grupo_factor'], r['gas']
                sheet, row_num, parent_row, expected_label = MAPPING[(category, group)]
                cells = source[sheet]
                label = str(cells[f'B{row_num}']).strip()
                assert label == expected_label, (year, sheet, row_num, label)
                parent_label = str(cells[f'B{parent_row}']).strip()
                assert parent_label.startswith(category), (year, parent_label, category)
                assert int(cells.get('K1', cells.get('J1'))) == year
                emission_col, factor_col = GAS_COLUMNS[gas]
                ad_cell, em_cell, fe_cell = f'C{row_num}', f'{emission_col}{row_num}', f'{factor_col}{row_num}'
                activity, emission = cells[ad_cell], cells[em_cell]
                reported_fe = cells[fe_cell]
                assert isinstance(activity, (int, float)) and activity > 0
                assert isinstance(emission, (int, float))
                calculated = emission * 1_000_000 / activity
                normalized_ief = reported_fe * (1000 if gas == 'CO2' else 1)
                current = float(r['valor_factor'])
                comparison = math.isclose(current, calculated, rel_tol=1e-9, abs_tol=1e-8)
                ief_comparison = math.isclose(current, normalized_ief, rel_tol=1e-9, abs_tol=1e-8)
                record = {
                    'registro_id': r['registro_id'], 'anio': year, 'categoria_ipcc': category,
                    'grupo_factor': group, 'gas': gas, 'archivo_crt': filename,
                    'sha256_xlsx': sha, 'hoja': sheet, 'etiqueta_categoria_crt': parent_label,
                    'etiqueta_grupo_crt': label, 'celda_actividad': ad_cell,
                    'actividad_crt_tj': activity, 'celda_emision': em_cell,
                    'emision_crt_kt_gas': emission, 'celda_ief_reportado': fe_cell,
                    'ief_reportado_original': reported_fe,
                    'unidad_ief_reportado': 't CO2/TJ' if gas == 'CO2' else f'kg {gas}/TJ',
                    'factor_calculado_kg_tj': calculated,
                    'factor_repositorio_kg_tj': current, 'diferencia_kg_tj': current - calculated,
                    'coincide_E_div_A': comparison, 'coincide_ief_reportado': ief_comparison,
                    'nota_compatibilidad': (
                        'El denominador incluye Jet kerosene cuya actividad también se reporta en aviación internacional; sus emisiones se reportan en Table1.D. Requiere conciliación de cobertura.'
                        if category == '1.A.3' and year >= 2019 else
                        'Mismo año, categoría y grupo CRT. Un factor agrupado no distingue combustibles dentro del grupo.')
                }
                report.append(record)
            for r in [t for t in fugitive_targets if int(t['anio']) == year]:
                sheet = 'Table1.B.2'
                cells = source[sheet]
                gas = r['gas']
                em_cell, fe_cell = {'CO2': ('I12', 'F12'), 'CH4': ('J12', 'G12'), 'N2O': ('K12', 'H12')}[gas]
                emission = cells.get(em_cell)
                if gas == 'N2O':
                    missing_n2o.append({'anio': year, 'registro_id': r['registro_id'], 'archivo_crt': filename,
                        'sha256_xlsx': sha, 'hoja': sheet, 'celda_emision': em_cell,
                        'emision': emission, 'celda_factor': fe_cell, 'factor': cells.get(fe_cell),
                        'emision_raw': wb.sheet(sheet).get(em_cell), 'factor_raw': wb.sheet(sheet).get(fe_cell)})
                    continue
                if not r['valor_factor'] or float(r['valor_factor']) <= 0:
                    continue
                extraction = [p for p in psut_rows if p['anio'] == str(year) and p['producto'] == 'PETR'
                              and p['lado'] == 'Supply' and p['bloque'] == 'A'
                              and p['unidad_sectorial'] == 'ENV' and p['metodo'] == 'EXTRACCION_B']
                assert len(extraction) == 1, (year, extraction)
                pr = extraction[0]
                activity = float(pr['TJ'])
                calculated = emission * 1_000_000 / activity
                current = float(r['valor_factor'])
                report.append({
                    'registro_id': r['registro_id'], 'anio': year, 'categoria_ipcc': r['categoria_ipcc'],
                    'grupo_factor': r['grupo_factor'], 'gas': gas, 'archivo_crt': filename,
                    'sha256_xlsx': sha, 'hoja': sheet, 'etiqueta_categoria_crt': cells['B12'],
                    'etiqueta_grupo_crt': 'Production and upgrading',
                    'celda_actividad': f"PSUT[{pr['registro_mapeo']}].TJ",
                    'actividad_crt_tj': None, 'actividad_psut_tj': activity,
                    'actividad_crt_original': cells.get('E12'), 'unidad_actividad_crt_original': cells.get('D12'),
                    'psut_registro_mapeo': pr['registro_mapeo'], 'psut_source_record_id': pr['source_record_id'],
                    'sha256_psut': source_hashes[str(PSUT)], 'celda_emision': em_cell,
                    'emision_crt_kt_gas': emission, 'celda_ief_reportado': fe_cell,
                    'ief_reportado_original': cells.get(fe_cell), 'unidad_ief_reportado': 'kg/unidad de actividad CRT; no kg/TJ',
                    'factor_calculado_kg_tj': calculated, 'factor_repositorio_kg_tj': current,
                    'diferencia_kg_tj': current - calculated,
                    'coincide_E_div_A': math.isclose(current, calculated, rel_tol=1e-9, abs_tol=1e-8),
                    'coincide_ief_reportado': None,
                    'nota_compatibilidad': 'Factor experimental = emisión CRT / extracción PETR PSUT. Denominador TJ distinto de actividad nativa CRT en 10^3 m^3. IEF CRT no se compara directamente con kg/TJ.',
                })
            t = source['Table1.A(a)s3']
            for row_num in [10, 11, 16, 17, 18, 20, 21, 22, 23]:
                transport_details.append({
                    'anio': year, 'archivo_crt': filename, 'sha256_xlsx': sha,
                    'hoja': 'Table1.A(a)s3', 'fila': row_num,
                    'etiqueta': t.get(f'B{row_num}'), 'celda_actividad': f'C{row_num}',
                    'actividad_tj': t.get(f'C{row_num}'),
                    **{f'{gas}_celda': f'{col}{row_num}' for gas, (col, _) in GAS_COLUMNS.items()},
                    **{f'{gas}_kt': t.get(f'{col}{row_num}') for gas, (col, _) in GAS_COLUMNS.items()},
                })
            d = source['Table1.D']
            raw_s3, raw_d = wb.sheet('Table1.A(a)s3'), wb.sheet('Table1.D')
            jet_ad = t.get('C18')
            jet_int_ad = d.get('C11')
            repeated = (isinstance(jet_ad, (int, float)) and isinstance(jet_int_ad, (int, float))
                        and jet_ad > 0 and math.isclose(jet_ad, jet_int_ad, rel_tol=1e-12, abs_tol=1e-8))
            num = lambda v: v if isinstance(v, (int, float)) else 0.0
            check = {
                'anio': year, 'archivo_crt': filename, 'sha256_xlsx': sha,
                'actividad_total_s3_C10_tj': t.get('C10'),
                'actividad_aviacion_domestica_s3_C16_tj': t.get('C16'),
                'actividad_gasolina_aviacion_s3_C17_tj': t.get('C17'),
                'actividad_jet_s3_C18_tj': jet_ad,
                'actividad_carretera_s3_C20_tj': t.get('C20'),
                'actividad_jet_internacional_1D_C11_tj': jet_int_ad,
                'jet_actividad_repetida_entre_tablas': repeated,
                'diferencia_actividad_C10_menos_C17_C18_C20_tj': t['C10']-sum(num(t.get(x)) for x in ['C17', 'C18', 'C20']),
                'jet_emision_domestica_CO2_celda_H18': t.get('H18'),
                'jet_emision_domestica_CH4_celda_I18': t.get('I18'),
                'jet_emision_domestica_N2O_celda_J18': t.get('J18'),
                'jet_CO2_internacional_1D_G11_kt': d.get('G11'),
                'jet_CH4_internacional_1D_H11_kt': d.get('H11'),
                'jet_N2O_internacional_1D_I11_kt': d.get('I11'),
                **{f'diferencia_{gas}_total_menos_gasolina_aviacion_y_carretera_kt':
                    t[f'{col}10']-num(t.get(f'{col}17'))-num(t.get(f'{col}20'))
                    for gas, (col, _) in GAS_COLUMNS.items()},
                'fraccion_AD_total_que_repite_jet_internacional': jet_ad/t['C10'] if repeated else None,
                'estado': 'Conciliar cobertura antes de interpretar como factor nacional completo.' if repeated
                          else 'No se observa actividad Jet kerosene duplicada en esta fila/año.',
            }
            transport_checks.append(check)
            transport_raw[str(year)] = {
                'Table1.A(a)s3': {c: raw_s3.get(c) for c in ['C10','C11','C16','C17','C18','C20','E11','F11','G11','H10','H16','H17','H18','I18','J18']},
                'Table1.D': {c: raw_d.get(c) for c in ['C10','C11','G10','G11','H11','I11','B28','B34','B35','B36']},
                'metadata': {name: wb.metadata[name] for name in ['Table1.A(a)s3','Table1.D']},
            }
            wb.z.close()
    for name, rows in [('cotejo_factores_crt_2018_2022.csv', report),
                       ('detalle_transporte_crt_original.csv', transport_details),
                       ('conciliacion_cobertura_transporte_crt.csv', transport_checks)]:
        with (OUT / name).open('w', encoding='utf-8', newline='') as f:
            fields = list(dict.fromkeys(key for r in rows for key in r))
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    (OUT / 'celdas_crt_2018_2022_generacion_transporte_comercial.json').write_text(
        json.dumps(all_cells, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {
        'zip_local': str(ZIP), 'zip_sha256': hashlib.sha256(ZIP.read_bytes()).hexdigest(),
        'zip_origen': 'Archivo ZIP original suministrado localmente al verificador. La procedencia de la copia debe conservarse con el informe.',
        'ficha_oficial': 'https://unfccc.int/documents/646206',
        'url_oficial_zip': 'https://unfccc.int/sites/default/files/resource/GTM-CRT-2024-V0.3-20250304-084824_started.zip',
        'verificacion_identidad': 'Nombres internos, país, versión y sello coinciden con publicación. Sin hash público remoto para comparación bit a bit.',
        'input_sha256': source_hashes, 'archivos_xlsx': manifest, 'factores_cotejados': len(report),
        'coinciden_E_div_A': sum(r['coincide_E_div_A'] for r in report),
        'coinciden_ief_reportado_combustion': sum(r['coincide_ief_reportado'] is True for r in report),
        'factores_fugitivos_con_denominador_PSUT': sum(r['categoria_ipcc'] == '1.B.2.a.ii' for r in report),
        'n2o_fugitivo_sin_emision_y_factor': sum(r['emision'] is None and r['factor'] is None for r in missing_n2o),
        'max_diferencia_absoluta_kg_tj': max(abs(r['diferencia_kg_tj']) for r in report),
        'precision_cotejo': 'math.isclose(rel_tol=1e-9, abs_tol=1e-8)',
        'hallazgo_transporte': 'En 2019–2022 C18 (Jet kerosene) de Table1.A(a)s3 aporta actividad igual a Table1.D C11, pero H18/I18/J18 están vacías y las emisiones se reportan en Table1.D G11/H11/I11. En 2018 C18 también está vacía. La causa de la doble ubicación no se determina aquí. No reclasificar actividad ni sumar emisiones de bunkers sin definir el alcance.',
    }
    (OUT / 'resumen_auditoria_factores_crt_2018_2022.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'evidencia_xml_cobertura_transporte.json').write_text(
        json.dumps(transport_raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'evidencia_xml_n2o_fugitivo.json').write_text(
        json.dumps(missing_n2o, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    compared_ids = [r['registro_id'] for r in report]
    assert len(set(compared_ids)) == len(compared_ids), 'Factores duplicados en el cotejo'
    assert set(compared_ids) == expected_positive_ids, 'Hay factores positivos sin cotejar o registros adicionales'
    assert source_hashes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ZIP, MODEL, PSUT]}, 'Fuentes modificadas durante auditoría'
    lines = [
        'AUDITORÍA DE FACTORES CONTRA CRT ORIGINALES 2018–2022',
        '',
        f"Factores positivos cotejados: {len(report)}. Coinciden: {summary['coinciden_E_div_A']}.",
        f"Combustión: {summary['coinciden_ief_reportado_combustion']} también coinciden con el IEF reportado, después de convertir t CO2/TJ a kg CO2/TJ.",
        f"Fugitivas: {summary['factores_fugitivos_con_denominador_PSUT']} reproducen emisión CRT / extracción PETR PSUT (TJ). No se confunde ese denominador con E12 del CRT, expresado en 10^3 m^3.",
        f"N2O fugitivo: {summary['n2o_fugitivo_sin_emision_y_factor']} años con factor H12 y emisión K12 vacíos en Table1.B.2. No equivalen a un cero medido.",
        f"Diferencia absoluta máxima: {summary['max_diferencia_absoluta_kg_tj']:.12g} kg/TJ.",
        f"ZIP SHA256: {summary['zip_sha256']}",
        'Referencia: https://unfccc.int/documents/646206',
        '',
        'TRANSPORTE: COINCIDENCIA ARITMÉTICA Y COBERTURA',
        summary['hallazgo_transporte'],
        'En cada año, C10 = C17 + C18 + C20 de Table1.A(a)s3 (sumando únicamente entradas numéricas). H10/I10/J10 = emisiones de gasolina de aviación y carretera, filas 17 y 20. Esto describe la suma publicada y no imputa cero a celdas vacías.',
        'Las celdas H18:J18 no contienen valores, fórmulas ni claves de notación; no hay combinaciones de celdas que oculten una emisión en esa fila. Table1.D, nota B28, establece que los búnkeres internacionales se reportan por separado del total nacional.',
        '',
        'Año; actividad jet coincidente (TJ); proporción del denominador agregado',
    ]
    for r in transport_checks:
        if r['jet_actividad_repetida_entre_tablas']:
            lines.append(f"{r['anio']}; {r['actividad_jet_s3_C18_tj']:.8f}; {100*r['fraccion_AD_total_que_repite_jet_internacional']:.6f}%")
    lines += [
        '',
        'Estos porcentajes describen la composición del denominador; no son una corrección aprobada de emisiones. No se establece la causa de la ubicación duplicada ni se determina aquí el perímetro correcto de la cuenta experimental.',
        'La conciliación de cobertura afecta la interpretación de los factores 1.A.3 de 2019–2022 y de su reutilización en años posteriores. La correspondencia entre combustibles individuales y factores agrupados sigue siendo un supuesto que no queda validado por la coincidencia del cociente.',
        'La auditoría no modifica insumos, factores ni resultados. Se conservaron los hashes de las tres fuentes antes y después de la lectura.',
        '',
        'REPRODUCIR',
        'python auditar_factores_crt_2018_2022.py --crt-zip RUTA_ZIP --entrada RUTA_REPOSITORIO --psut RUTA_CSV_PSUT --salida RUTA_EVIDENCIA',
        'Solo requiere la biblioteca estándar de Python. El ZIP original debe obtenerse por separado. Los hashes y las celdas se incluyen en los CSV y JSON producidos.',
    ]
    (OUT / 'revision_factores_crt_2018_2022.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('No coincidentes:', [r for r in report if not r['coincide_E_div_A']])
    print('Años con actividad de jet coincidente en ambas tablas:', [r['anio'] for r in transport_checks if r['jet_actividad_repetida_entre_tablas']])
    if any(not r['coincide_E_div_A'] for r in report):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
