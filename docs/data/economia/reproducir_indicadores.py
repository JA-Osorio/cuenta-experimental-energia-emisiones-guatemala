"""Reproduce indicadores nacionales. Ejecutar desde cualquier directorio.
Uso: python docs/data/economia/reproducir_indicadores.py [salida.csv]
Solo biblioteca estándar de Python; lee el Excel original y la PSUT del repositorio.
"""
from pathlib import Path
import csv, hashlib, json, sys, xml.etree.ElementTree as ET, zipfile
from math import fsum

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
meta = json.loads((HERE / 'pib_real_2018_2024.json').read_text(encoding='utf-8'))
xlsx = HERE / meta['archivo']
assert hashlib.sha256(xlsx.read_bytes()).hexdigest() == meta['sha256'], 'El Excel cambió'
ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(xlsx) as z:
    cells = {c.attrib['r']: float(c.find('s:v', ns).text)
             for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:c', ns)
             if c.attrib.get('t') != 's' and c.find('s:v', ns) is not None}
psut = ROOT / '02_resultados_y_diccionario/psut_energia_guatemala_2018_2024.csv'
assert hashlib.sha256(psut.read_bytes()).hexdigest() == '4be0edefa6d24be0598a0c8cdbb5a7fc76211bed3dfc205083d60a18398bc071', 'La PSUT cambió; revisar procedencia antes de reproducir'
with psut.open(encoding='utf-8-sig', newline='') as f:
    records = list(csv.DictReader(f))

def final(r):
    return r['lado'] == 'Use' and (
        (r['bloque'] in ('E', 'F') and r['unidad_sectorial'] in ('HH', 'TR_BEN', 'IND_BEN', 'SERV') and r['metodo'] != 'USO_NO_ENERGETICO_APARENTE')
        or r['metodo'] == 'USO_ENERGETICO_INTERNO_APARENTE')

uses = {y: fsum(float(r['TJ']) for r in records if int(r['anio']) == y and final(r)) for y in range(2018, 2025)}
rows = []
for source in meta['series']:
    y = source['anio']; pib = cells[source['celda']]; use = uses[y]
    assert pib == source['pib_real_millones_Q']
    rows.append(dict(anio=y, pib_real_millones_Q=pib, uso_final_ampliado_TJ=use,
                     intensidad_TJ_por_millon_Q=use/pib, productividad_millones_Q_por_TJ=pib/use,
                     indice_pib_2018_100=pib/cells['I18']*100,
                     indice_uso_final_2018_100=use/uses[2018]*100, estado_pib=source['estado_pib'],
                     unidad_pib=meta['unidad'], fuente_pib=meta['url'], fecha_consulta_pib=meta['fecha_consulta'],
                     archivo_pib_sha256=meta['sha256'],
                     fuente_psut='https://github.com/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala',
                     revision_psut='57439f2920851336b271f5788b859f518dfb1bf2',
                     definicion_energia='Uso final ampliado: uso identificado + uso energético no asignado; excluye usos no energéticos, transformación y consumo propio energético.'))
output = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'indicadores_economia_energia_2018_2024.csv'
with output.open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f'{output}: {len(rows)} años, 2018–2024')
