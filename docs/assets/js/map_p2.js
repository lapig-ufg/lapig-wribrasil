// ──────────────────────────────────────────────────────────
//  PRODUCT 2 VIEWER — Training Set, Condition Series + SOM,
//  Field Points (100) and 2025a / 2025b Pasture Maps
// ──────────────────────────────────────────────────────────
(function () {
  'use strict';

  const mapEl = document.getElementById('map-p2');
  if (!mapEl || typeof L === 'undefined') return;

  const BASE = (window.siteBaseUrl || '') + '/assets/p2/';
  const CENTER = [-15.5, -49.5];
  const ZOOM = 5;

  const TIPOLOGIAS = {
    'PASTO PRODUTIVO': { color: '#faea40', label: 'Productive Pasture' },
    'PASTO COM ERVAS': { color: '#d8ff6c', label: 'Pasture with Weeds' },
    'PASTO COM LENHOSAS': { color: '#66c600', label: 'Pasture with Shrubs / Trees' },
    'INTERMEDIARIO': { color: '#f4b346', label: 'Intermediate Pasture' },
    'DEG BIOLOGICA': { color: '#813209', label: 'Biological Degradation' },
    'REG NATURAL': { color: '#0e5f0e', label: 'Natural Regeneration' },
    'MISCELANEA': { color: '#ec2b10', label: 'Miscellaneous' }
  };
  const DECISOES = [
    { key: 'CLEAN', label: 'Clean (keep)', color: '#2b8a3e' },
    { key: 'ANALYZE', label: 'Analyze (inspect)', color: '#f08c00' },
    { key: 'REMOVE', label: 'Remove', color: '#c92a2a' }
  ];
  const LABELS = [
    { key: 1, label: 'Pasture', color: '#f2b705' },
    { key: 0, label: 'Non-pasture', color: '#4c6ef5' }
  ];
  const ANOS = { treino: [2020, 2021, 2022, 2023, 2024, 2025], condicao: [2019, 2020, 2021, 2022, 2023, 2024, 2025] };

  const state = {
    ds: 'treino', year: 2025, som: '90', rule: 'D', colorBy: 'dec',
    labels: new Set([0, 1]), fontesT: new Set([0, 1]),
    decisoes: new Set([0, 1, 2]), tips: new Set([0, 1, 2, 3, 4, 5, 6, -1]), fontesC: new Set([0, 1, 2])
  };
  const cache = {};

  // ── Map & basemaps ──
  const renderer = L.canvas({ padding: 0.5 });
  const map = L.map('map-p2', { center: CENTER, zoom: ZOOM, preferCanvas: true, scrollWheelZoom: true });
  const esri = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  const attr = '&copy; <a href="https://www.esri.com/">Esri</a> · LAPIG/UFG · WRI Brasil';
  const basemaps = {
    gray: L.layerGroup([
      L.tileLayer(esri + 'Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', { attribution: attr, maxNativeZoom: 16, maxZoom: 19 }),
      L.tileLayer(esri + 'Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 16, maxZoom: 19 })
    ]),
    satellite: L.layerGroup([
      L.tileLayer(esri + 'World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: attr, maxNativeZoom: 19, maxZoom: 19 }),
      L.tileLayer(esri + 'Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 19, maxZoom: 19 })
    ]),
    topo: L.tileLayer(esri + 'World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { attribution: attr, maxNativeZoom: 18, maxZoom: 19 })
  };
  let basemap = basemaps.gray.addTo(map);
  document.getElementById('p2-basemap').addEventListener('change', (e) => {
    map.removeLayer(basemap);
    basemap = basemaps[e.target.value].addTo(map);
    basemap.bringToBack && basemap.bringToBack();
  });
  document.getElementById('p2-reset').addEventListener('click', () => map.setView(CENTER, ZOOM));
  setTimeout(() => map.invalidateSize(), 250);
  window.addEventListener('resize', () => map.invalidateSize());

  // ── 2025a / 2025b raster tiles ──
  map.createPane('rasters');
  map.getPane('rasters').style.zIndex = 350;
  const BLANK = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
  const rasterBounds = L.latLngBounds([-25.0, -61.5], [-2.0, -40.5]);
  function rasterLayer(nome, attribution) {
    return L.tileLayer(BASE + 'tiles/' + nome + '/{z}/{x}/{y}.png', {
      pane: 'rasters', minZoom: 0, maxZoom: 19, minNativeZoom: 5, maxNativeZoom: 11, bounds: rasterBounds,
      errorTileUrl: BLANK, opacity: 0.8, attribution: attribution
    });
  }
  const rasters = {
    a: rasterLayer('2025a', 'LAPIG/Cenargen pasture maps 2025'),
    b: rasterLayer('2025b', 'LAPIG/Cenargen pasture maps 2025'),
    mb: rasterLayer('mb2025', 'MapBiomas 10 m Collection 4'),
    gpw: rasterLayer('gpw2022', 'Global Pasture Watch v1'),
    gpwnat: rasterLayer('gpwnat2022', 'Global Pasture Watch v1')
  };
  Object.keys(rasters).forEach(k => {
    const cb = document.getElementById('p2-raster-' + k);
    const op = document.getElementById('p2-op-' + k);
    cb.addEventListener('change', () => cb.checked ? rasters[k].addTo(map) : map.removeLayer(rasters[k]));
    op.addEventListener('input', () => rasters[k].setOpacity(op.value / 100));
    op.addEventListener('click', (e) => e.stopPropagation());
  });

  // ── Field points (100) ──
  map.createPane('campo');
  map.getPane('campo').style.zIndex = 450;
  const campoRenderer = L.svg({ pane: 'campo' });
  const campoLayer = L.layerGroup();
  const AGREE = { 'Concorda': 'Agreement', 'Discorda parcialmente': 'Partial disagreement', 'Discorda totalmente': 'Full disagreement' };
  const CLASSE_SCORE = { ND: 'Not degraded', PD: 'Partially degraded', SD: 'Severely degraded' };
  const VIGOR = { baixo: 'low', 'médio': 'medium', medio: 'medium', alto: 'high' };
  function traduz(s) {
    return s.replace(/Concorda|Discorda parcialmente|Discorda totalmente/g, m => AGREE[m])
      .replace(/\b(baixo|médio|medio|alto)\b/g, m => VIGOR[m]);
  }
  let campoCarregado = false;
  const btnCampo = document.getElementById('p2-btn-campo');
  btnCampo.addEventListener('click', () => {
    if (map.hasLayer(campoLayer)) {
      map.removeLayer(campoLayer);
      btnCampo.classList.remove('p2-on');
      return;
    }
    btnCampo.classList.add('p2-on');
    campoLayer.addTo(map);
    if (campoCarregado) return;
    fetch(BASE + 'campo_100.json').then(r => r.json()).then(d => {
      campoCarregado = true;
      d.data.forEach(p => {
        const cls = (p.classe_2022 || '').split(' ')[0];
        L.circleMarker([p.lat, p.lon], { pane: 'campo', renderer: campoRenderer, radius: 7, color: '#111', weight: 1.5, fillColor: p.cor, fillOpacity: 0.95 })
          .bindPopup(
            '<strong>Field point ' + p.nome + '</strong><br>' +
            'Stratum: ' + traduz(p.estrato.replace(/\s*\(\d+\)$/, '')) + '<br>' +
            'Interpreter class 2022: ' + (CLASSE_SCORE[cls] ? CLASSE_SCORE[cls] + ' (' + p.classe_2022 + ')' : p.classe_2022) + '<br>' +
            'Vigor 2025: ' + traduz(p.vigor_2025) + '<br>' +
            'Weight: ' + p.peso + '<br>Grid: ' + p.grade + '<br>' +
            p.lat.toFixed(4) + ', ' + p.lon.toFixed(4))
          .addTo(campoLayer);
      });
    });
  });

  // ── Sample points ──
  const pontosLayer = L.layerGroup().addTo(map);
  const loading = document.getElementById('p2-loading');

  function load(ds, year) {
    const key = ds + '_' + year;
    if (cache[key]) return Promise.resolve(cache[key]);
    loading.style.display = 'block';
    return fetch(BASE + ds + '_' + year + '.json').then(r => r.json()).then(d => {
      const idx = {};
      d.cols.forEach((c, i) => { idx[c] = i; });
      d.idx = idx;
      cache[key] = d;
      loading.style.display = 'none';
      return d;
    });
  }

  function fmt(n) { return n.toLocaleString('en-US'); }

  function render() {
    pontosLayer.clearLayers();
    if (state.ds === 'nenhum') {
      setCounter(0, 'Sample points hidden', '');
      return;
    }
    const ds = state.ds, year = state.year;
    load(ds, year).then(d => {
      if (ds !== state.ds || year !== state.year) return;
      pontosLayer.clearLayers();
      const I = d.idx;
      const counts = {};
      let n = 0;
      d.data.forEach((r, i) => {
        let color, ok;
        if (ds === 'treino') {
          ok = state.labels.has(r[I.label]) && state.fontesT.has(r[I.fonte]);
          color = r[I.label] === 1 ? LABELS[0].color : LABELS[1].color;
        } else {
          const dec = r[I['dec' + state.rule + state.som]];
          const tip = r[I.classe];
          ok = state.decisoes.has(dec) && state.tips.has(tip) && state.fontesC.has(r[I.fonte]);
          if (state.colorBy === 'dec') color = dec >= 0 ? DECISOES[dec].color : '#888';
          else color = tip >= 0 ? TIPOLOGIAS[d.tipologias[tip]].color : '#888';
          if (ok) counts[dec] = (counts[dec] || 0) + 1;
        }
        if (!ok) return;
        n++;
        const m = L.circleMarker([r[I.lat], r[I.lon]], {
          renderer, radius: 3, weight: 0.4, color: 'rgba(0,0,0,0.45)', fillColor: color, fillOpacity: 0.9
        });
        m.on('click', () => m.bindPopup(popup(d, r)).openPopup());
        m.addTo(pontosLayer);
      });
      const total = d.data.length;
      if (ds === 'treino') {
        setCounter(n, 'Training Set Points · ' + year, Math.round(100 * n / total) + '% of ' + fmt(total) + ' points visible');
      } else {
        const partes = DECISOES.map((x, i) => x.key[0] + x.key.slice(1).toLowerCase() + ' ' + fmt(counts[i] || 0));
        setCounter(n, 'Condition Series · SOM ' + state.som + '×' + state.som + ' · ' + year,
          Math.round(100 * n / total) + '% of ' + fmt(total) + ' visible · ' + partes.join(' · '));
      }
    });
  }

  function popup(d, r) {
    const I = d.idx;
    const ll = r[I.lat].toFixed(5) + ', ' + r[I.lon].toFixed(5);
    if (state.ds === 'treino') {
      return '<strong>' + (r[I.label] === 1 ? 'Pasture' : 'Non-pasture') + '</strong> · ' + d.year + '<br>' +
        'Class: ' + d.classes[r[I.classe]] + '<br>Source: ' + d.fontes[r[I.fonte]] + '<br>' +
        'IBGE sheet: ' + d.cartas[r[I.carta]] + '<br>' + ll;
    }
    const tip = r[I.classe] >= 0 ? TIPOLOGIAS[d.tipologias[r[I.classe]]].label : 'n/a';
    const linha = (s) => {
      const dom = r[I['dom' + s]];
      const decN = r[I['decN' + s]], decD = r[I['decD' + s]];
      return '<tr><td>' + s + '×' + s + '</td><td>' + r[I['n' + s]] + '</td><td>' +
        (dom >= 0 ? TIPOLOGIAS[d.tipologias[dom]].label : 'n/a') + '</td><td>' + (r[I['pur' + s]] ?? '') + '</td><td>' +
        (decD >= 0 ? d.decisoes[decD] : '') + '</td><td>' + (decN >= 0 ? d.decisoes[decN] : '') + '</td></tr>';
    };
    return '<strong>' + tip + '</strong> · ' + d.year + '<br>' +
      'Source: ' + d.fontes[r[I.fonte]] + '<br>Md3: ' + (r[I.md3] ?? 'n/a') + '<br>' + ll +
      '<table style="margin-top:6px;font-size:0.72rem;border-collapse:collapse" cellpadding="2">' +
      '<tr><th>SOM</th><th>Neuron</th><th>Dominant</th><th>Purity</th><th>Dirichlet</th><th>Normal</th></tr>' +
      linha('90') + linha('35') + '</table>';
  }

  function setCounter(n, label, sub) {
    document.getElementById('p2-counter').textContent = fmt(n);
    document.getElementById('p2-counter-label').textContent = label;
    document.getElementById('p2-counter-sub').textContent = sub;
  }

  // ── Panel controls ──
  function checkList(containerId, items, set) {
    const el = document.getElementById(containerId);
    el.innerHTML = '';
    items.forEach(it => {
      const lab = document.createElement('label');
      lab.className = 'checkbox-label';
      lab.innerHTML = '<input type="checkbox" checked> <span class="p2-swatch" style="background:' + (it.color || '#ccc') + '"></span> ' + it.label;
      lab.querySelector('input').addEventListener('change', (e) => {
        e.target.checked ? set.add(it.key) : set.delete(it.key);
        render();
      });
      el.appendChild(lab);
    });
  }
  checkList('p2-labels', LABELS, state.labels);
  checkList('p2-fontes-treino', [{ key: 0, label: 'Collection 4 Sentinel-2', color: '#adb5bd' }, { key: 1, label: 'MapBiomas 85k Landsat', color: '#495057' }], state.fontesT);
  checkList('p2-decisoes', DECISOES.map((x, i) => ({ key: i, label: x.label, color: x.color })), state.decisoes);
  checkList('p2-tipologias', Object.keys(TIPOLOGIAS).map((k, i) => ({ key: i, label: TIPOLOGIAS[k].label, color: TIPOLOGIAS[k].color }))
    .concat([{ key: -1, label: 'No field match', color: '#888' }]), state.tips);
  checkList('p2-fontes-condicao', [
    { key: 0, label: '50k Base (CVP)', color: '#adb5bd' },
    { key: 1, label: 'MapBiomas Pasture (Col. 11)', color: '#868e96' },
    { key: 2, label: 'MapBiomas 85k Landsat (pasture)', color: '#495057' }], state.fontesC);

  function buildYears() {
    const el = document.getElementById('p2-years');
    el.innerHTML = '';
    const anos = ANOS[state.ds] || [];
    if (!anos.includes(state.year)) state.year = anos[anos.length - 1];
    anos.slice().reverse().forEach(y => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'p2-chip' + (y === state.year ? ' active' : '');
      b.textContent = y;
      b.addEventListener('click', () => {
        state.year = y;
        el.querySelectorAll('.p2-chip').forEach(c => c.classList.toggle('active', c === b));
        render();
      });
      el.appendChild(b);
    });
  }

  document.querySelectorAll('[data-p2ds]').forEach(btn => {
    btn.addEventListener('click', () => {
      state.ds = btn.dataset.p2ds;
      document.querySelectorAll('[data-p2ds]').forEach(b => b.classList.toggle('active', b === btn));
      document.getElementById('p2-filtros-treino').style.display = state.ds === 'treino' ? '' : 'none';
      document.getElementById('p2-filtros-condicao').style.display = state.ds === 'condicao' ? '' : 'none';
      buildYears();
      render();
    });
  });

  function chipGroup(attr, key) {
    document.querySelectorAll('[' + attr + ']').forEach(btn => {
      btn.addEventListener('click', () => {
        state[key] = btn.getAttribute(attr);
        document.querySelectorAll('[' + attr + ']').forEach(b => b.classList.toggle('active', b === btn));
        render();
      });
    });
  }
  chipGroup('data-p2som', 'som');
  chipGroup('data-p2rule', 'rule');
  chipGroup('data-p2color', 'colorBy');

  buildYears();
  render();
})();
