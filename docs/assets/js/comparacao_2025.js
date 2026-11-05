// ──────────────────────────────────────────────────────────
//  PASTURE MAP COMPARISON 2025 — 2025a × 2025b × MapBiomas × GPW
//  (preliminary, threshold >= 50): charts + 0.25° cell map
// ──────────────────────────────────────────────────────────
(function () {
  'use strict';

  if (!document.getElementById('comparacao-2025') || typeof Chart === 'undefined') return;

  const BASE = (window.siteBaseUrl || '') + '/assets/p2/comparacao/';
  const fmt1 = (v) => v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fmt2 = (v) => v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const FONT = { family: 'Inter, system-ui, sans-serif', size: 11 };
  Chart.defaults.font.family = FONT.family;
  Chart.defaults.color = '#475569';
  Chart.defaults.locale = 'en-US';

  const MAP_COLORS = { a: '#e8590c', b: '#6741d9', MB: '#d4a017', GPW: '#1c7ed6', GPWnat: '#2f9e44' };
  const ARB = { esp: '#495057', gpw: '#1c7ed6' };

  fetch(BASE + 'comparacao_2025.json').then(r => r.json()).then(D => {
    tiles(D);
    chartAreas(D);
    chartConcord(D);
    cellMap(D);
    chartCats(D);
    chartClasses(D);
    tableCats(D);
    janelas(D);
    chartAttr(D);
    chartP5(D);
    chartP6(D);
    validacao(D);
  });

  // ── Summary tiles ──
  function tiles(D) {
    const r = D.resumo;
    const t = [
      [fmt1(r.area_mha) + ' Mha', 'Cerrado area analyzed'],
      [fmt1(r.past_mha.a) + ' / ' + fmt1(r.past_mha.b), 'Mha of pasture in 2025a / 2025b'],
      [fmt1(r.past_mha.MB) + ' Mha', 'Pasture in MapBiomas 2025'],
      [fmt1(r.past_mha.GPW) + ' / ' + fmt1(r.past_mha.GPWnat), 'Mha of cultivated / natural grassland in GPW 2022'],
      [fmt1(r.a_dif_b) + '%', 'Of the area where 2025a ≠ 2025b'],
      [fmt1(r.concord_mb.a) + '% / ' + fmt1(r.concord_mb.b) + '%', 'Agreement of a / b with MapBiomas']
    ];
    document.getElementById('cmp-tiles').innerHTML =
      t.map(x => '<div class="cmp-tile"><b>' + x[0] + '</b><span>' + x[1] + '</span></div>').join('');
  }

  function chartAreas(D) {
    const p = D.resumo.past_mha;
    new Chart(document.getElementById('cmp-chart-areas'), {
      type: 'bar',
      data: {
        labels: ['2025a', '2025b', 'MapBiomas 2025', ['GPW 2022', 'cultivated'], ['GPW 2022', 'natural']],
        datasets: [{ data: [p.a, p.b, p.MB, p.GPW, p.GPWnat], backgroundColor: [MAP_COLORS.a, MAP_COLORS.b, MAP_COLORS.MB, MAP_COLORS.GPW, MAP_COLORS.GPWnat], borderRadius: 4 }]
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => fmt1(c.raw) + ' Mha (' + fmt1(c.raw / D.resumo.area_mha * 100) + '% of the Cerrado)' } } },
        scales: { y: { beginAtZero: true, title: { display: true, text: 'Mha' } }, x: { grid: { display: false } } }
      }
    });
  }

  function chartConcord(D) {
    const r = D.resumo;
    new Chart(document.getElementById('cmp-chart-concord'), {
      type: 'bar',
      data: {
        labels: ['2025a', '2025b', 'MapBiomas'],
        datasets: [
          { label: 'vs MapBiomas 2025', data: [r.concord_mb.a, r.concord_mb.b, null], backgroundColor: MAP_COLORS.MB, borderRadius: 4 },
          { label: 'vs GPW 2022 (cultivated)', data: [r.concord_gpw.a, r.concord_gpw.b, r.concord_gpw.MB], backgroundColor: MAP_COLORS.GPW, borderRadius: 4 }
        ]
      },
      options: {
        maintainAspectRatio: false,
        plugins: { tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + fmt1(c.raw) + '%' } } },
        scales: { y: { min: 50, max: 100, title: { display: true, text: '% of area in agreement' } }, x: { grid: { display: false } } }
      }
    });
  }

  // ── 0.25° cell map ──
  function cellMap(D) {
    const map = L.map('map-cmp', { center: [-14.5, -49], zoom: 5, preferCanvas: true, scrollWheelZoom: true });
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution: '&copy; Esri · LAPIG/UFG · WRI Brasil', maxNativeZoom: 16, maxZoom: 12
    }).addTo(map);
    map.createPane('labels');
    map.getPane('labels').style.zIndex = 450;
    map.getPane('labels').style.pointerEvents = 'none';
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
      pane: 'labels', maxNativeZoom: 16, maxZoom: 12
    }).addTo(map);
    setTimeout(() => map.invalidateSize(), 250);

    const G = D.grade, I = {};
    G.cols.forEach((c, i) => { I[c] = i; });
    const renderer = L.canvas({ padding: 0.3 });
    const cats = D.categorias;

    const seq = ['#ffffe5', '#fff7bc', '#fee391', '#fec44f', '#fe9929', '#ec7014', '#cc4c02', '#8c2d04'];
    const div = ['#2166ac', '#4393c3', '#92c5de', '#d1e5f0', '#f7f7f7', '#fddbc7', '#f4a582', '#d6604d', '#b2182b'];
    const vir = ['#440154', '#46327e', '#365c8d', '#277f8e', '#1fa187', '#4ac16d', '#a0da39', '#fde725'];
    const civ = ['#00224e', '#233e6c', '#575d6d', '#7c7b78', '#a59c74', '#d3c064', '#fee838'];
    const ramp = (pal, t) => pal[Math.max(0, Math.min(pal.length - 1, Math.round(t * (pal.length - 1))))];

    const VARS = {
      A: { lab: '2025a pasture (% of cell)', kind: 'seq', get: r => r[I.A], min: 0, max: 80 },
      B: { lab: '2025b pasture (% of cell)', kind: 'seq', get: r => r[I.B], min: 0, max: 80 },
      M: { lab: 'MapBiomas 2025 pasture (% of cell)', kind: 'seq', get: r => r[I.M], min: 0, max: 80 },
      G: { lab: 'GPW 2022 cultivated grassland (% of cell)', kind: 'seq', get: r => r[I.G], min: 0, max: 80 },
      N: { lab: 'GPW 2022 natural / semi-natural grassland (% of cell)', kind: 'seq', get: r => r[I.N], min: 0, max: 80 },
      MA: { lab: 'MapBiomas − 2025a (p.p.; blue: MB has more)', kind: 'div', get: r => r[I.M] - r[I.A], v: 20, inv: true },
      MB: { lab: 'MapBiomas − 2025b (p.p.; blue: MB has more)', kind: 'div', get: r => r[I.M] - r[I.B], v: 20, inv: true },
      MG: { lab: 'MapBiomas − GPW 2022 cultivated (p.p.; blue: MB has more)', kind: 'div', get: r => r[I.M] - r[I.G], v: 40, inv: true },
      AB: { lab: '2025a − 2025b (p.p.; red: a has more)', kind: 'div', get: r => r[I.A] - r[I.B], v: 3 },
      pred: { lab: 'Predominant difference', kind: 'cat', get: r => r[I.pred], n: 6 },
      pred4: { lab: 'Predominant among 1–4 (where a ≠ b)', kind: 'cat', get: r => r[I.pred4], n: 4 },
      a_dif_b: { lab: 'a ≠ b (% of cell)', kind: 'vir', get: r => r[I.a_dif_b], min: 0, max: 3 },
      comum: { lab: 'Differences shared by a and b (%)', kind: 'civ', get: r => r[I.comum], min: 50, max: 100 }
    };

    function color(v, cfg) {
      if (v === null || v === undefined || Number.isNaN(v)) return null;
      if (cfg.kind === 'cat') return v > 0 ? cats[v - 1].cor : null;
      if (cfg.kind === 'div') {
        const t = (Math.max(-cfg.v, Math.min(cfg.v, v)) + cfg.v) / (2 * cfg.v);
        return ramp(div, cfg.inv ? 1 - t : t);
      }
      const t = (v - cfg.min) / (cfg.max - cfg.min);
      return ramp(cfg.kind === 'vir' ? vir : cfg.kind === 'civ' ? civ : seq, t);
    }

    const layer = L.layerGroup().addTo(map);
    const rects = G.data.map(r => {
      const x = G.x0 + r[I.ix] * G.passo, y = G.y0 + r[I.iy] * G.passo;
      const rect = L.rectangle([[y, x], [y + G.passo, x + G.passo]], { renderer, stroke: false, fillOpacity: 0.85 });
      rect.on('click', () => {
        const p = (v) => (v === null ? 'n/a' : fmt1(v) + '%');
        rect.bindPopup(
          '<strong>Cell ' + fmt2(y + G.passo / 2) + ', ' + fmt2(x + G.passo / 2) + '</strong><br>' +
          'Valid area: ' + fmt1(r[I.area_kha]) + ' kha<br>' +
          'Pasture share: a ' + p(r[I.A]) + ' · b ' + p(r[I.B]) + ' · MB ' + p(r[I.M]) + '<br>GPW 2022: cultivated ' + p(r[I.G]) + ' · natural ' + p(r[I.N]) + '<br>' +
          'Predominant difference: ' + (r[I.pred] > 0 ? r[I.pred] + ' — ' + cats[r[I.pred] - 1].nome : 'none') + '<br>' +
          'a ≠ b: ' + fmt2(r[I.a_dif_b]) + '% of cell · shared differences: ' + p(r[I.comum])
        ).openPopup();
      });
      rect.addTo(layer);
      return { rect, r };
    });

    const sel = document.getElementById('cmp-var');
    const op = document.getElementById('cmp-op');
    function update() {
      const cfg = VARS[sel.value];
      const opacity = op.value / 100;
      rects.forEach(({ rect, r }) => {
        const c = color(cfg.get(r), cfg);
        rect.setStyle(c ? { fillColor: c, fillOpacity: opacity } : { fillOpacity: 0 });
      });
      legend(cfg);
    }
    function legend(cfg) {
      const el = document.getElementById('cmp-legend');
      if (cfg.kind === 'cat') {
        el.innerHTML = '<strong>' + cfg.lab + '</strong>' + cats.slice(0, cfg.n).map(c =>
          '<div class="item"><span class="sw" style="background:' + c.cor + '"></span>' + c.cat + ': ' + c.nome + '</div>').join('');
        return;
      }
      let pal, lo, hi;
      if (cfg.kind === 'div') { pal = cfg.inv ? div.slice().reverse() : div; lo = '−' + cfg.v; hi = '+' + cfg.v; }
      else { pal = cfg.kind === 'vir' ? vir : cfg.kind === 'civ' ? civ : seq; lo = cfg.min; hi = cfg.max + (cfg.kind === 'seq' ? '+' : ''); }
      el.innerHTML = '<strong>' + cfg.lab + '</strong><div class="bar" style="background: linear-gradient(90deg,' + pal.join(',') + ')"></div>' +
        '<div class="ticks"><span>' + lo + '</span><span>0</span><span>' + hi + '</span></div>';
      if (cfg.kind !== 'div') el.querySelector('.ticks').innerHTML = '<span>' + lo + '</span><span>' + hi + '</span>';
    }
    sel.addEventListener('change', update);
    op.addEventListener('input', update);
    update();
  }

  // ── Six differences ──
  function chartCats(D) {
    const c = D.categorias;
    new Chart(document.getElementById('cmp-chart-cats'), {
      type: 'bar',
      data: {
        labels: c.map(x => 'Cat. ' + x.cat),
        datasets: [{ data: c.map(x => x.mha), backgroundColor: c.map(x => x.cor), borderColor: 'rgba(0,0,0,0.25)', borderWidth: 1, borderRadius: 3 }]
      },
      options: {
        indexAxis: 'y', maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { title: (it) => c[it[0].dataIndex].cat + ': ' + c[it[0].dataIndex].nome, label: (ctx) => fmt2(c[ctx.dataIndex].mha) + ' Mha · ' + fmt2(c[ctx.dataIndex].pct) + '% of the Cerrado' } } },
        scales: { x: { beginAtZero: true, title: { display: true, text: 'Mha' } }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } }
      }
    });
  }

  function chartClasses(D) {
    const c = D.categorias;
    const nomes = [];
    c.forEach(x => Object.keys(x.classes_mb).forEach(k => { if (!nomes.includes(k)) nomes.push(k); }));
    const PAL = { 'Pasture': '#edde8e', 'Mosaic of Uses': '#ffefc3', 'Savanna Formation': '#32cd32', 'Temporary Crop': '#e974ed',
      'Grassland': '#b8af4f', 'Forest Formation': '#1f8d49', 'Forest Plantation': '#7a5900', 'Wetland': '#519799',
      'Other Non-Vegetated': '#db4d4f', 'Urban Area': '#d4271e', 'Other classes': '#bbbbbb' };
    new Chart(document.getElementById('cmp-chart-classes'), {
      type: 'bar',
      data: {
        labels: c.map(x => 'Cat. ' + x.cat),
        datasets: nomes.map(n => ({ label: n, data: c.map(x => x.classes_mb[n] || 0), backgroundColor: PAL[n] || '#999', borderColor: 'rgba(0,0,0,0.15)', borderWidth: 1 }))
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
          tooltip: { callbacks: { title: (it) => c[it[0].dataIndex].cat + ': ' + c[it[0].dataIndex].nome, label: (ctx) => ctx.dataset.label + ': ' + fmt1(ctx.raw) + '%' }, filter: (it) => it.raw > 0 }
        },
        scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, max: 100, title: { display: true, text: '% of category area' } } }
      }
    });
  }

  function tableCats(D) {
    const rows = D.categorias.map(x => {
      const cl = Object.entries(x.classes_mb).filter(([k]) => k !== 'Other classes').slice(0, 4).map(([k, v]) => k + ' ' + Math.round(v) + '%').join('; ');
      return '<tr><td><span class="cmp-legend"><span class="sw" style="display:inline-block;vertical-align:-1px;margin-right:6px;background:' + x.cor + '"></span></span>' + x.cat + '</td>' +
        '<td>' + x.nome + '</td><td class="n">' + fmt2(x.mha) + '</td><td class="n">' + fmt2(x.pct) + '%</td><td>' + cl + '</td>' +
        '<td class="n">' + x.gpw_past + '%</td><td class="n">' + x.gpw_natural + '%</td><td class="n">' + x.prob_espectral + '%</td></tr>';
    }).join('');
    document.getElementById('cmp-table-cats').innerHTML =
      '<thead><tr><th>#</th><th>Category</th><th class="n">Mha</th><th class="n">% Cerrado</th><th>Class in MapBiomas</th>' +
      '<th class="n">GPW: pasture</th><th class="n">GPW: natural grassland</th><th class="n">Spectral pasture prob.</th></tr></thead><tbody>' + rows + '</tbody>';
  }

  // ── Sentinel-2 windows ──
  function janelas(D) {
    const tabs = document.getElementById('cmp-tabs-jan');
    const img = document.getElementById('cmp-img-jan');
    const cap = document.getElementById('cmp-cap-jan');
    function show(c) {
      img.src = BASE + 'janelas_cat' + c.cat + '.jpg';
      cap.textContent = 'Category ' + c.cat + ': ' + c.nome + '. Columns: Sentinel-2 dry season (Jul–Sep) and rainy season (Jan–Apr) 2025, 2025a, 2025b, MapBiomas 2025, GPW 2022, and the six-color difference map.';
      tabs.querySelectorAll('.cmp-tab').forEach(b => b.classList.toggle('active', +b.dataset.cat === c.cat));
    }
    D.categorias.forEach(c => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cmp-tab';
      b.dataset.cat = c.cat;
      b.innerHTML = '<span class="sw" style="display:inline-block;width:10px;height:10px;border-radius:2px;border:1px solid rgba(0,0,0,.2);background:' + c.cor + '"></span>Category ' + c.cat;
      b.title = c.nome;
      b.addEventListener('click', () => show(c));
      tabs.appendChild(b);
    });
    show(D.categorias[0]);
  }

  function chartAttr(D) {
    const NOMES = {
      ndvi_p10: 'NDVI 10th percentile (2025)', ndvi_p50: 'NDVI median (2025)', ndvi_p90: 'NDVI 90th percentile (2025)', ndvi_amp: 'NDVI amplitude (2025)',
      ndvi_sd: 'NDVI standard deviation (2025)', chuva_ndvi: 'NDVI rainy season', chuva_nbr: 'NBR rainy season', chuva_ndmi: 'NDMI rainy season',
      chuva_B4: 'B4 red, rainy season', chuva_B8: 'B8 NIR, rainy season', chuva_B11: 'B11 SWIR1, rainy season', chuva_B12: 'B12 SWIR2, rainy season',
      seca_ndvi: 'NDVI dry season', seca_nbr: 'NBR dry season', seca_ndmi: 'NDMI dry season', seca_B4: 'B4 red, dry season', seca_B8: 'B8 NIR, dry season',
      seca_B11: 'B11 SWIR1, dry season', seca_B12: 'B12 SWIR2, dry season', elev: 'Elevation (m)', decliv: 'Slope (°)',
      n_obs_s2: 'Sentinel-2 valid observations', prob_a: '2025a probability', prob_b: '2025b probability'
    };
    const EST = ['000', '111', '100', '010', '110', '011', '101', '001'];
    const COR = { '000': '#868e96', '111': '#2b8a3e', '100': '#e31a1c', '011': '#fb9a99', '010': '#ffd700', '101': '#fff3a0', '110': '#6a3d9a', '001': '#cab2d6' };
    const sel = document.getElementById('cmp-attr');
    Object.keys(D.atributos).forEach(k => {
      const o = document.createElement('option');
      o.value = k; o.textContent = NOMES[k] || k;
      if (k === 'seca_ndvi') o.selected = true;
      sel.appendChild(o);
    });
    const chart = new Chart(document.getElementById('cmp-chart-attr'), {
      type: 'bar',
      data: { labels: EST, datasets: [{ data: [], backgroundColor: EST.map(e => COR[e]), borderColor: 'rgba(0,0,0,0.3)', borderWidth: 1, borderRadius: 3 }] },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { title: (it) => 'Stratum ' + it[0].label + ' (a b MB)' } } },
        scales: { x: { grid: { display: false }, title: { display: true, text: 'Stratum (a b MB)' } } }
      }
    });
    function upd() {
      chart.data.datasets[0].data = EST.map(e => D.atributos[sel.value][e]);
      chart.update();
    }
    sel.addEventListener('change', upd);
    upd();
  }

  // ── Steps 5 & 6 ──
  function arbChart(id, rows, labels) {
    new Chart(document.getElementById(id), {
      type: 'bar',
      data: {
        labels: rows.map(r => r.estrato + ' · ' + r.nome),
        datasets: labels.map(l => ({ label: l.lab, data: rows.map(r => r[l.key]), backgroundColor: l.cor, borderRadius: 3 }))
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
          tooltip: { callbacks: { afterTitle: (it) => fmt2(rows[it[0].dataIndex].mha) + ' Mha', label: (c) => c.dataset.label + ': ' + c.raw + '%' } }
        },
        scales: { y: { min: 0, max: 100, title: { display: true, text: '% of sample points' } }, x: { grid: { display: false }, ticks: { font: { size: 10 }, autoSkip: false, maxRotation: 0, callback: function (v) { return this.getLabelForValue(v).split(' · '); } } } }
      }
    });
  }
  function chartP5(D) {
    arbChart('cmp-chart-p5', D.passo5, [
      { key: 'esp_a', lab: 'Spectral agrees with a', cor: MAP_COLORS.a },
      { key: 'esp_b', lab: 'Spectral agrees with b', cor: MAP_COLORS.b },
      { key: 'gpw_a', lab: 'GPW agrees with a', cor: '#ffa94d' },
      { key: 'gpw_b', lab: 'GPW agrees with b', cor: '#b197fc' }
    ]);
  }
  function chartP6(D) {
    arbChart('cmp-chart-p6', D.passo6, [
      { key: 'esp_ab', lab: 'Spectral agrees with a/b', cor: MAP_COLORS.a },
      { key: 'esp_mb', lab: 'Spectral agrees with MapBiomas', cor: MAP_COLORS.MB },
      { key: 'gpw_ab', lab: 'GPW agrees with a/b', cor: '#ffa94d' },
      { key: 'gpw_mb', lab: 'GPW agrees with MapBiomas', cor: '#ffe066' }
    ]);
  }

  // ── Validation plan ──
  function validacao(D) {
    const v = D.validacao;
    new Chart(document.getElementById('cmp-chart-val'), {
      data: {
        labels: v.map(x => x.estrato),
        datasets: [
          { type: 'bar', label: 'Area (Mha)', data: v.map(x => x.mha), backgroundColor: '#ced4da', yAxisID: 'y', borderRadius: 3 },
          { type: 'line', label: 'Sample points', data: v.map(x => x.pontos), borderColor: '#e8590c', backgroundColor: '#e8590c', yAxisID: 'y2', tension: 0, pointRadius: 4 }
        ]
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10 } },
          tooltip: { callbacks: { title: (it) => 'Stratum ' + v[it[0].dataIndex].estrato + ': ' + v[it[0].dataIndex].nome } }
        },
        scales: {
          y: { type: 'logarithmic', min: 0.1, max: 200, title: { display: true, text: 'Area (Mha, log)' }, ticks: { callback: (v) => ([0.1, 1, 10, 100].includes(v) ? v : '') } },
          y2: { position: 'right', min: 0, max: 180, grid: { drawOnChartArea: false }, title: { display: true, text: 'Points' } },
          x: { grid: { display: false }, title: { display: true, text: 'Stratum (a b MB)' } }
        }
      }
    });
    const tot = v.reduce((s, x) => s + x.pontos, 0);
    document.getElementById('cmp-table-val').innerHTML =
      '<thead><tr><th>Stratum</th><th>Situation</th><th class="n">Mha</th><th class="n">Points</th><th class="n">ha per point</th></tr></thead><tbody>' +
      v.map(x => '<tr><td>' + x.estrato + '</td><td>' + x.nome + '</td><td class="n">' + fmt2(x.mha) + '</td><td class="n">' + x.pontos +
        '</td><td class="n">' + x.ha_por_ponto.toLocaleString('en-US') + '</td></tr>').join('') +
      '<tr><td colspan="3"><strong>Total</strong></td><td class="n"><strong>' + tot + '</strong></td><td></td></tr></tbody>';
  }
})();
