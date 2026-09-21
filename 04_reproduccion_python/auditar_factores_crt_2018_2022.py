"""Auditoría de factores con procedencia CRT 2018–2022 contra XLSX V0.3.

No modifica el ZIP, los XLSX fuente ni los archivos del repositorio.
Los parámetros BTR/IPCC quedan fuera de este cotejo; su verificación requiere
sus propias fuentes. GAS transporte se reconstruye con las filas 17 + 21.
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
CRT_SOURCE_ID = 'UNFCCC_GTM_CRT_2024'
TRANSPORT_MAPPING = {
    ('1.A.3', 'COMB_GAS'): (
        'Table1.A(a)s3', (17, 21), 10, ('Aviation gasoline', 'Gasoline')),
    ('1.A.3', 'COMB_DOIL'): (
        'Table1.A(a)s3', (22,), 10, ('Diesel oil',)),
    ('1.A.3', 'COMB_GLP'): (
        'Table1.A(a)s3', (23,), 10, ('Liquefied petroleum gases (LPG)',)),
}


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
        crt_rows = [r for r in model_rows
                    if r['tipo_registro'] == 'FACTOR_EMISION_OBS'
                    and r['fuente_id'] == CRT_SOURCE_ID
                    and 2018 <= int(r['anio']) <= 2022]
        target = [r for r in crt_rows
                  if (r['categoria_ipcc'], r['grupo_factor']) in MAPPING.keys() | TRANSPORT_MAPPING.keys()
                  and r['valor_factor'] and float(r['valor_factor']) > 0]
        fugitive_targets = [r for r in crt_rows
                            if r['categoria_ipcc'] == '1.B.2.a.ii']
    with PSUT.open(encoding='utf-8-sig') as f:
        psut_rows = list(csv.DictReader(f))
    source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ZIP, MODEL, PSUT]}
    expected_positive_ids = {r['registro_id'] for r in crt_rows
                             if r['valor_factor'] and float(r['valor_factor']) > 0}
    outside_scope = [r for r in model_rows
                     if r.get('valor_factor') and float(r['valor_factor']) > 0
                     and r['fuente_id'] != CRT_SOURCE_ID]
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
                key = (category, group)
                if key in TRANSPORT_MAPPING:
                    sheet, row_nums, parent_row, expected_labels = TRANSPORT_MAPPING[key]
                else:
                    sheet, row_num, parent_row, expected_label = MAPPING[key]
                    row_nums, expected_labels = (row_num,), (expected_label,)
                cells = source[sheet]
                labels = tuple(str(cells[f'B{n}']).strip() for n in row_nums)
                assert labels == expected_labels, (year, sheet, row_nums, labels)
                label = ' + '.join(labels)
                parent_label = str(cells[f'B{parent_row}']).strip()
                assert parent_label.startswith(category), (year, parent_label, category)
                assert int(cells.get('K1', cells.get('J1'))) == year
                emission_col, factor_col = GAS_COLUMNS[gas]
                ad_cells = [f'C{n}' for n in row_nums]
                em_cells = [f'{emission_col}{n}' for n in row_nums]
                fe_cells = [f'{factor_col}{n}' for n in row_nums]
                activities = [cells[c] for c in ad_cells]
                emissions = [cells[c] for c in em_cells]
                reported_factors = [cells[c] for c in fe_cells]
                assert all(isinstance(v, (int, float)) and v > 0 for v in activities)
                assert all(isinstance(v, (int, float)) for v in emissions + reported_factors)
                activity, emission = sum(activities), sum(emissions)
                ad_cell, em_cell, fe_cell = ('+'.join(v) for v in (ad_cells, em_cells, fe_cells))
                # For GAS no single IEF cell exists: reconstruct the activity-weighted
                # IEF of the two fuels, and distinguish it from a reported scalar.
                reported_fe = (reported_factors[0] if len(row_nums) == 1 else
                               sum(a * f for a, f in zip(activities, reported_factors)) / activity)
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
                    'ief_reportado_original': reported_factors[0] if len(row_nums) == 1 else None,
                    'ief_ponderado_unidad_original': reported_fe if len(row_nums) > 1 else None,
                    'metodo_cotejo_ief': 'PONDERADO_POR_TJ_DE_IEF_REPORTADOS' if len(row_nums) > 1 else 'IEF_REPORTADO_DIRECTO',
                    'estado_factor_modelo': r['estado'], 'fuente_id_modelo': r['fuente_id'],
                    'actividad_componentes_tj': json.dumps(activities),
                    'emision_componentes_kt_gas': json.dumps(emissions),
                    'ief_componentes_originales': json.dumps(reported_factors),
                    'formula_reconstruccion': f'1000000*({em_cell})/({ad_cell})',
                    'unidad_ief_reportado': 't CO2/TJ' if gas == 'CO2' else f'kg {gas}/TJ',
                    'factor_calculado_kg_tj': calculated,
                    'factor_repositorio_kg_tj': current, 'diferencia_kg_tj': current - calculated,
                    'coincide_E_div_A': comparison, 'coincide_ief_reportado': ief_comparison,
                    'nota_compatibilidad': (
                        'GAS reúne gasolina de aviación y de motor, BTR1 p. 66. Cociente de sumas (cálculo CAL); aplicación PRX supone representatividad de la mezcla anual CRT respecto de BEN. No usa C18 ni Table1.D.'
                        if group == 'COMB_GAS' else
                        'Combustible específico de la categoría CRT 1.A.3.b. BTR1 pp. 64–65 describe navegación no desagregable dentro de esta categoría; no equivale a una medición exclusivamente vial. No usa C18 ni Table1.D.'
                        if group in {'COMB_DOIL', 'COMB_GLP'} else
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
        'criterio_alcance': f'Factores de 2018–2022 con fuente_id={CRT_SOURCE_ID}, incluidos estados OBS y PRX. Los parámetros de otras fuentes no se atribuyen a CRT.',
        'factores_crt_positivos_en_entrada': len(expected_positive_ids),
        'parametros_positivos_de_otras_fuentes_fuera_de_alcance': len(outside_scope),
        'fuentes_fuera_de_alcance': sorted({r['fuente_id'] for r in outside_scope}),
        'factores_transporte_por_producto': sum(r['grupo_factor'] in {'COMB_GAS', 'COMB_DOIL', 'COMB_GLP'} for r in report),
        'factores_gasolina_con_ief_ponderado': sum(r.get('metodo_cotejo_ief') == 'PONDERADO_POR_TJ_DE_IEF_REPORTADOS' for r in report),
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
    assert set(compared_ids) == expected_positive_ids, 'Hay factores CRT positivos sin cotejar o registros adicionales'
    assert source_hashes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ZIP, MODEL, PSUT]}, 'Fuentes modificadas durante auditoría'
    lines = [
        'AUDITORÍA DE FACTORES CONTRA CRT ORIGINALES 2018–2022',
        '',
        f"Factores positivos cotejados: {len(report)}. Coinciden: {summary['coinciden_E_div_A']}.",
        summary['criterio_alcance'],
        f"Parámetros positivos de otras fuentes fuera de alcance: {len(outside_scope)}. Fuentes: {', '.join(summary['fuentes_fuera_de_alcance']) or 'ninguna'}.",
        f"Combustión: {summary['coinciden_ief_reportado_combustion']} coinciden con IEF publicados o su promedio ponderado por TJ, después de convertir t CO2/TJ a kg CO2/TJ.",
        f"Transporte por producto: {summary['factores_transporte_por_producto']} factores. GAS: {summary['factores_gasolina_con_ief_ponderado']} reconstruyen suma de emisiones / suma de actividad de filas 17+21; DOIL usa fila 22; GLP usa fila 23.",
        'GAS agrega gasolina de aviación y de motor; el cálculo se deriva de datos oficiales, pero su aplicación mantiene PRX por el supuesto de representatividad de la mezcla CRT respecto de BEN. DOIL/GLP conservan la cobertura de la categoría reportada, que incluye navegación no desagregada según BTR1 pp. 64–65.',
        f"Fugitivas: {summary['factores_fugitivos_con_denominador_PSUT']} reproducen emisión CRT / extracción PETR PSUT (TJ). No se confunde ese denominador con E12 del CRT, expresado en 10^3 m^3.",
        f"N2O fugitivo: {summary['n2o_fugitivo_sin_emision_y_factor']} años con factor H12 y emisión K12 vacíos en Table1.B.2. No equivalen a un cero medido.",
        f"Diferencia absoluta máxima: {summary['max_diferencia_absoluta_kg_tj']:.12g} kg/TJ.",
        f"ZIP SHA256: {summary['zip_sha256']}",
        'Referencia: https://unfccc.int/documents/646206',
        '',
        'COBERTURA DE TRANSPORTE',
        'COMB_GAS, COMB_DOIL y COMB_GLP utilizan las filas 17+21, 22 y 23 de Table1.A(a)s3, respectivamente. El queroseno de transporte utiliza los parámetros IPCC documentados en la NT-02 y queda fuera de este cotejo CRT.',
        'El archivo conciliacion_cobertura_transporte_crt.csv documenta la composición del agregado CRT y la correspondencia de actividad entre sus tablas como control de cobertura de la fuente.',
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
