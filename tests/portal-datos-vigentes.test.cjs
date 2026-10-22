const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const portal = require("../docs/datos-vigentes.js");

const root = path.resolve(__dirname, "..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const energy = read("02_resultados_y_diccionario/psut_energia_guatemala_2018_2024.csv");
const emissions = read("02_resultados_y_diccionario/cuenta_emisiones_aire_guatemala_2018_2024.csv");
const economy = JSON.parse(read("docs/data/economia/pib_real_2018_2024.json"));
const parts = Array.from({ length: 6 }, (_, i) => read("docs/portal-" + String(i).padStart(2, "0") + ".part"));
const html = parts.join("");
const revision = "a".repeat(40);
const metadata = { sha: revision, commit: { committer: { date: "2026-10-22T21:00:00Z" } } };
const now = new Date("2026-10-23T01:00:00Z");
const prepare = (a = energy, b = emissions, c = economy) => portal.prepare(a, b, c, metadata, now);
const firstTJ = portal.parseCSV(energy)[0].TJ;

test("los gases sin cuantificar permanecen vacíos y los ceros se conservan", () => {
  const sampleEnergy = "registro_mapeo,anio,producto,flow_group,lado,bloque,unidad_sectorial,TJ\nMAP_TEST,2024,PETR,Energy products,Supply,A,ENV,12.5\n";
  const sampleEmissions = "clave_emision,anio,unidad_sectorial_agregada,modulo,producto_std,co2_directo_kt,co2_biogenico_memo_kt,ch4_kt,n2o_kt,co2e_kt\nEM_TEST,2024,B,FUGITIVAS,PETR,1,0,2,,57\n";
  const snapshot = prepare(sampleEnergy, sampleEmissions);
  const oil = snapshot.emissions[0];
  assert.equal(oil.n2o_kt, null);
  assert.equal(oil.co2_biogenico_memo_kt, 0);
  assert.equal(snapshot.psut[0].TJ, 12.5);
  assert.equal(snapshot.consulta, "22 de octubre de 2026");
  assert.equal(snapshot.commit, revision);
});

test("el CSV admite notas con comas, comillas y saltos de línea", () => {
  assert.deepEqual(portal.parseCSV('\uFEFFid,nota\r\n1,"Leña, ""hogares""\r\nsegunda línea"\r\n'),
    [{ id: "1", nota: 'Leña, "hogares"\r\nsegunda línea' }]);
  assert.throws(() => portal.parseCSV('id,nota\n1,"sin cerrar'), /sin cerrar/);
});

test("un cambio en los CSV llega al portal sin modificar el paquete de visualización", async () => {
  const newTJ = Number(firstTJ) + 1;
  const changed = energy.replace("," + firstTJ + ",", "," + newTJ + ",");
  const requests = [];
  const fetcher = async (url, options) => {
    requests.push({ url, options });
    let value;
    if (url.endsWith("/commits/main")) value = metadata;
    else {
      assert.ok(url.includes("/" + revision + "/"), "todos los archivos usan la misma revisión");
      if (url.endsWith("psut_energia_guatemala_2018_2024.csv")) value = changed;
      else if (url.endsWith("cuenta_emisiones_aire_guatemala_2018_2024.csv")) value = emissions;
      else if (url.endsWith("pib_real_2018_2024.json")) value = economy;
      else {
        const match = url.match(/portal-(\d\d)\.part$/);
        assert.ok(match, "recurso conocido");
        value = parts[Number(match[1])];
      }
    }
    return { ok: true, text: async () => value, json: async () => value };
  };
  const result = await portal.load(fetcher);
  assert.equal(result.snapshot.psut[0].TJ, newTJ);
  assert.ok(result.html.includes('"TJ":' + newTJ));
  assert.equal(requests.length, 10);
  assert.ok(requests.every(r => r.options.cache === "no-store" && r.options.credentials === "omit"));
  assert.ok(!result.html.includes("raw.githubusercontent.com/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala/main/"));
  assert.ok(result.html.includes("raw.githubusercontent.com/JA-Osorio/cuenta-experimental-energia-emisiones-guatemala/" + revision + "/"));
  assert.ok(result.html.includes("(0,Ca.useState)(Co[Co.length-1])"));
  const script = result.html.slice(result.html.indexOf("<script>") + 8, result.html.lastIndexOf("</script>"));
  assert.doesNotThrow(() => new vm.Script(script));
});

test("una consulta fallida no muestra la instantánea antigua", async () => {
  await assert.rejects(portal.load(async () => ({ ok: false })), /fuente vigente/);
});

test("se rechazan números inválidos y fuentes con coberturas incompatibles", () => {
  assert.throws(() => prepare(energy.replace("," + firstTJ + ",", ",sin dato,")), /numérico inválido/);
  const missing = Object.assign({}, economy, { series: economy.series.filter(r => r.anio !== 2024) });
  assert.throws(() => prepare(energy, emissions, missing), /PIB no disponible/);
});

test("las notas del CSV no pueden cerrar el script del portal", () => {
  const snapshot = prepare();
  snapshot.psut[0].nota = "</script><script>throw 'injected'</script>";
  const output = portal.hydrate(html, snapshot);
  assert.ok(!output.includes("</script><script>throw"));
  assert.ok(output.includes("\\u003c/script>\\u003cscript>"));
  assert.throws(() => portal.hydrate(html.replace("var le=LA,Co=", "var datos=LA,Co="), snapshot),
    /estructura del portal/);
});
