/* Carga los datos y las descargas desde una única revisión de main. */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.PortalVigente = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var REPOSITORY = "JA-Osorio/cuenta-experimental-energia-emisiones-guatemala";
  var RAW = "https://raw.githubusercontent.com/" + REPOSITORY;
  var ENERGY = "02_resultados_y_diccionario/psut_energia_guatemala_2018_2024.csv";
  var EMISSIONS = "02_resultados_y_diccionario/cuenta_emisiones_aire_guatemala_2018_2024.csv";
  var GDP = "docs/data/economia/pib_real_2018_2024.json";

  function parseCSV(text) {
    var rows = [], row = [], field = "", quoted = false;
    text = text.replace(/^\uFEFF/, "");
    for (var i = 0; i < text.length; i++) {
      var c = text[i];
      if (quoted) {
        if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
        else if (c === '"') quoted = false;
        else field += c;
      } else if (c === '"') {
        if (field !== "") throw new Error("CSV: comillas fuera de lugar.");
        quoted = true;
      } else if (c === ",") {
        row.push(field); field = "";
      } else if (c === "\r" || c === "\n") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(field);
        if (row.some(function (v) { return v !== ""; })) rows.push(row);
        row = []; field = "";
      } else field += c;
    }
    if (quoted) throw new Error("CSV: campo sin cerrar.");
    if (row.length || field !== "") { row.push(field); rows.push(row); }
    if (rows.length < 2) throw new Error("CSV sin registros.");
    var header = rows.shift();
    if (new Set(header).size !== header.length || header.some(function (h) { return !h; }))
      throw new Error("CSV: encabezados inválidos.");
    return rows.map(function (r) {
      if (r.length !== header.length) throw new Error("CSV: cantidad de columnas inválida.");
      return Object.fromEntries(header.map(function (h, index) { return [h, r[index]]; }));
    });
  }

  function normalize(rows, required, numeric, nullable, id) {
    required.forEach(function (field) {
      if (!Object.prototype.hasOwnProperty.call(rows[0], field))
        throw new Error("Falta la columna " + field + ".");
    });
    var ids = new Set();
    return rows.map(function (original) {
      var row = Object.assign({}, original);
      if (!row[id] || ids.has(row[id])) throw new Error("Identificador vacío o duplicado.");
      ids.add(row[id]);
      numeric.forEach(function (field) {
        var value = row[field].trim();
        if (value === "" && nullable.indexOf(field) !== -1) row[field] = null;
        else {
          if (value === "" || !Number.isFinite(Number(value)))
            throw new Error("Valor numérico inválido en " + field + ".");
          row[field] = Number(value);
        }
      });
      if (!Number.isInteger(row.anio)) throw new Error("Año inválido.");
      return row;
    });
  }

  function prepare(energyText, emissionsText, economy, metadata, now) {
    var psut = normalize(parseCSV(energyText),
      ["registro_mapeo", "anio", "producto", "flow_group", "lado", "bloque", "unidad_sectorial", "TJ"],
      ["anio", "TJ"], [], "registro_mapeo");
    var gases = ["co2_directo_kt", "co2_biogenico_memo_kt", "ch4_kt", "n2o_kt", "co2e_kt"];
    var emissions = normalize(parseCSV(emissionsText),
      ["clave_emision", "anio", "unidad_sectorial_agregada", "modulo", "producto_std"].concat(gases),
      ["anio"].concat(gases), gases, "clave_emision");
    var years = Array.from(new Set(psut.map(function (r) { return r.anio; }))).sort(function (a, b) { return a - b; });
    var emissionYears = Array.from(new Set(emissions.map(function (r) { return r.anio; }))).sort(function (a, b) { return a - b; });
    if (JSON.stringify(years) !== JSON.stringify(emissionYears))
      throw new Error("Las cuentas tienen coberturas temporales distintas.");
    if (!economy || !Array.isArray(economy.series)) throw new Error("Serie de PIB inválida.");
    var gdp = new Map(economy.series.map(function (r) { return [r.anio, r]; }));
    years.forEach(function (year) {
      var row = gdp.get(year);
      if (!row || !Number.isFinite(row.pib_real_millones_Q) || row.pib_real_millones_Q <= 0)
        throw new Error("PIB no disponible para " + year + ".");
    });
    if (!metadata || !/^[a-f0-9]{40}$/.test(metadata.sha)) throw new Error("Revisión inválida.");
    var checked = now || new Date();
    return {
      psut: psut, emissions: emissions, economia: economy, years: years,
      commit: metadata.sha,
      date: metadata.commit.committer.date.slice(0, 10),
      checkedAt: checked.toISOString(),
      consulta: new Intl.DateTimeFormat("es-GT", {
        day: "numeric", month: "long", year: "numeric", timeZone: "America/Guatemala"
      }).format(checked),
      repository: "https://github.com/" + REPOSITORY
    };
  }

  function replaceOnce(text, needle, replacement) {
    var index = text.indexOf(needle);
    if (index < 0 || text.indexOf(needle, index + needle.length) !== -1)
      throw new Error("La estructura del portal cambió; revise la integración de datos.");
    return text.slice(0, index) + replacement + text.slice(index + needle.length);
  }

  function safeJSON(value) {
    return JSON.stringify(value).replace(/</g, "\\u003c")
      .replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");
  }

  function hydrate(html, snapshot) {
    html = replaceOnce(html,
      "var le=LA,Co=[2018,2019,2020,2021,2022,2023,2024],Fi=",
      "var le=Object.assign(LA," + safeJSON(snapshot) + "),Co=le.years,Fi=");
    html = replaceOnce(html, "var PA=Hi,Ea=Co.map",
      "Hi=le.economia;var PA=Hi,Ea=Co.map");
    html = replaceOnce(html, "(0,Ca.useState)(2024)",
      "(0,Ca.useState)(Co[Co.length-1])");
    html = replaceOnce(html, 'children:"Instant\\xE1nea consultada"',
      'children:"Datos consultados"');
    html = replaceOnce(html, 'children:"21 de septiembre de 2026"',
      "children:le.consulta");
    html = replaceOnce(html, '"617 registros \\xB7 CSV"',
      'le.psut.length+" registros \\xB7 CSV"');
    html = replaceOnce(html, '"374 registros \\xB7 CSV"',
      'le.emissions.length+" registros \\xB7 CSV"');
    // Las descargas conservan la revisión de los datos que el visitante está viendo.
    return html.split(RAW + "/main/").join(RAW + "/" + snapshot.commit + "/");
  }

  async function request(url, type, fetcher) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 20000);
    try {
      var response = await fetcher(url, {
        cache: "no-store", credentials: "omit", signal: controller.signal
      });
      if (!response.ok) throw new Error("No se pudo consultar la fuente vigente.");
      return type === "json" ? await response.json() : await response.text();
    } finally { clearTimeout(timer); }
  }

  async function load(fetcher) {
    fetcher = fetcher || globalThis.fetch.bind(globalThis);
    var metadata = await request("https://api.github.com/repos/" + REPOSITORY + "/commits/main", "json", fetcher);
    if (!/^[a-f0-9]{40}$/.test(metadata.sha || "")) throw new Error("Revisión inválida.");
    var base = RAW + "/" + metadata.sha + "/";
    var paths = [ENERGY, EMISSIONS, GDP];
    for (var i = 0; i < 6; i++) paths.push("docs/portal-" + String(i).padStart(2, "0") + ".part");
    var files = await Promise.all(paths.map(function (path, index) {
      return request(base + path, index === 2 ? "json" : "text", fetcher);
    }));
    var snapshot = prepare(files[0], files[1], files[2], metadata);
    return { html: hydrate(files.slice(3).join(""), snapshot), snapshot: snapshot };
  }

  return { parseCSV: parseCSV, prepare: prepare, hydrate: hydrate, load: load };
});
