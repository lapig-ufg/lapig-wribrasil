// ──────────────────────────────────────────────────────────
//  FIELD CAMPAIGN PLANNING — 469 scored points, 100 selected
//  (3×3 stratified random), routes of the two campaigns
// ──────────────────────────────────────────────────────────
(function () {
  'use strict';

  const mapEl = document.getElementById('map-campo');
  if (!mapEl || typeof L === 'undefined') return;

  const URL = (window.siteBaseUrl || '') + '/assets/campo/planejamento_campo.json';
  const CLASSE = { ND: { c: '#2ca03c', l: 'ND · not degraded' }, PD: { c: '#ffc20e', l: 'PD · partially degraded' }, SD: { c: '#d62728', l: 'SD · severely degraded' } };
  const CVP = { 1: { c: '#d62728', l: 'Vigor 1 · low' }, 2: { c: '#ffc20e', l: 'Vigor 2 · medium' }, 3: { c: '#2ca03c', l: 'Vigor 3 · high' }, null: { c: '#adb5bd', l: 'No CVP 2025' } };
  const TIPO = { 'Agreement': '#2ca03c', 'Partial disagreement': '#ffc20e', 'Full disagreement': '#d62728' };
  const CAMP = { 1: '#1c7ed6', 2: '#e8590c' };
  const fmt = (v, d = 1) => v === null || v === undefined ? '–' : v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

  const map = L.map('map-campo', { center: [-16.2, -49.4], zoom: 7, preferCanvas: true });
  const esri = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  const attr = '&copy; Esri · LAPIG/UFG · WRI Brasil';
  const basemaps = {
    gray: L.layerGroup([L.tileLayer(esri + 'Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', { attribution: attr, maxNativeZoom: 16, maxZoom: 19 }),
      L.tileLayer(esri + 'Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 16, maxZoom: 19 })]),
    satellite: L.layerGroup([L.tileLayer(esri + 'World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: attr, maxNativeZoom: 19, maxZoom: 19 }),
      L.tileLayer(esri + 'Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 19, maxZoom: 19 })]),
    topo: L.tileLayer(esri + 'World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { attribution: attr, maxNativeZoom: 18, maxZoom: 19 })
  };
  let basemap = basemaps.gray.addTo(map);
  document.getElementById('fc-basemap').addEventListener('change', (e) => {
    map.removeLayer(basemap);
    basemap = basemaps[e.target.value].addTo(map);
  });
  setTimeout(() => map.invalidateSize(), 250);
  window.addEventListener('resize', () => map.invalidateSize());

  ['rotas', 'pontos', 'sel', 'num'].forEach((p, i) => { map.createPane(p); map.getPane(p).style.zIndex = 410 + i * 10; });
  const svgSel = L.svg({ pane: 'sel' });

  fetch(URL).then(r => r.json()).then(D => {
    const state = { camp: 0, dia: 0, colorBy: 'classe' };
    const layers = { pontos: L.layerGroup(), sel: L.layerGroup(), rotas: L.layerGroup(), acesso: L.layerGroup(), num: L.layerGroup() };
    const selById = {};
    D.selecionados.forEach(p => { selById[p.id] = p; });

    // stats
    const totKm = D.resumo.reduce((s, c) => s + c.km, 0);
    const totDias = D.resumo.reduce((s, c) => s + c.dias, 0);
    document.getElementById('fc-stats').innerHTML = [
      [D.total_score, 'Points with interpreter score (' + D.pontos.length + ' with coordinates)'], [D.selecionados.length, 'Points selected for revisit'],
      [D.resumo.length, 'Field campaigns'], [totDias, 'Field days'], [fmt(totKm, 0) + ' km', 'Total driving distance']
    ].map(x => '<div class="fc-stat"><b>' + x[0] + '</b><span>' + x[1] + '</span></div>').join('');

    // sampling design matrix (population = points with score and CVP)
    const N = {}, n = {};
    D.pontos.forEach(p => { if (p.cvp) { const k = p.classe + p.cvp; N[k] = (N[k] || 0) + 1; } });
    D.selecionados.forEach(p => { const k = p.classe + p.cvp; n[k] = (n[k] || 0) + 1; });
    const ESPERADO = { ND: 3, PD: 2, SD: 1 };
    const tipoCel = (cl, v) => (ESPERADO[cl] === v ? 'Agreement' : Math.abs(ESPERADO[cl] - v) === 1 ? 'Partial disagreement' : 'Full disagreement');
    const tot = (o) => Object.values(o).reduce((s, x) => s + x, 0);
    document.getElementById('fc-matriz').innerHTML =
      '<thead><tr><th>Class</th><th class="n">Vigor 1</th><th class="n">Vigor 2</th><th class="n">Vigor 3</th><th class="n">Total</th></tr></thead><tbody>' +
      ['ND', 'PD', 'SD'].map(cl => '<tr><td title="' + CLASSE[cl].l + '">' + cl + '</td>' + [1, 2, 3].map(v =>
        '<td class="n" style="background:' + TIPO[tipoCel(cl, v)] + '33" title="' + tipoCel(cl, v) + '">' + (N[cl + v] || 0) + ' / ' + (n[cl + v] || 0) + '</td>').join('') +
        '<td class="n">' + [1, 2, 3].reduce((s, v) => s + (N[cl + v] || 0), 0) + ' / ' + [1, 2, 3].reduce((s, v) => s + (n[cl + v] || 0), 0) + '</td></tr>').join('') +
      '<tr><td><strong>Total</strong></td>' + [1, 2, 3].map(v => '<td class="n">' + ['ND', 'PD', 'SD'].reduce((s, cl) => s + (N[cl + v] || 0), 0) + ' / ' +
        ['ND', 'PD', 'SD'].reduce((s, cl) => s + (n[cl + v] || 0), 0) + '</td>').join('') + '<td class="n"><strong>' + tot(N) + ' / ' + tot(n) + '</strong></td></tr></tbody>';

    // base
    L.marker([D.base.lat, D.base.lon], {
      icon: L.divIcon({ className: '', html: '<div style="background:#111;color:#fff;border-radius:4px;padding:2px 6px;font:700 11px sans-serif;white-space:nowrap">UFG</div>', iconAnchor: [16, 10] }),
      pane: 'num'
    }).bindPopup('<strong>Base</strong><br>' + D.base.nome).addTo(map);

    function visivel(p) {
      return (!state.camp || p.campanha === state.camp) && (!state.dia || p.dia === state.dia);
    }

    function draw() {
      Object.values(layers).forEach(l => l.clearLayers());
      // all scored points
      D.pontos.forEach(p => {
        const cfg = state.colorBy === 'classe' ? CLASSE[p.classe] : CVP[p.cvp];
        L.circleMarker([p.lat, p.lon], { pane: 'pontos', radius: 4, weight: 0.6, color: 'rgba(0,0,0,0.5)', fillColor: cfg.c, fillOpacity: 0.85 })
          .bindPopup('<strong>' + p.id + '</strong>' + (p.sel ? ' · <em>selected</em>' : '') + '<br>' +
            'Interpreter class: ' + CLASSE[p.classe].l + '<br>Mean score: ' + fmt(p.score, 2) + ' (' + fmt(p.smin) + '–' + fmt(p.smax) + ', ' + p.n + ' interpreters)<br>' +
            'CVP 2025: ' + CVP[p.cvp].l + '<br>Grid: ' + p.grade + ' · ' + p.loc)
          .addTo(layers.pontos);
      });
      // routes
      D.rotas.forEach(r => {
        if (!visivel(r)) return;
        L.polyline(r.coords, { pane: 'rotas', color: CAMP[r.campanha], weight: state.dia ? 4.5 : 3, opacity: 0.85 })
          .bindPopup('<strong>Campaign ' + r.campanha + ' · Day ' + r.dia + '</strong><br>' + r.de + ' → ' + r.para + '<br>' +
            fmt(r.km) + ' km · ' + fmt(r.horas_viagem, 2) + ' h' + (r.pct_terra ? '<br>Dirt road: ' + fmt(r.pct_terra) + '%' : ''))
          .addTo(layers.rotas);
      });
      D.acesso.forEach(a => {
        const p = selById[a.OLDNAME];
        if (!p || !visivel(p)) return;
        L.polyline(a.coords, { pane: 'rotas', color: '#111', weight: 2, dashArray: '4 4', opacity: 0.9 })
          .bindPopup('Off-road access to ' + a.OLDNAME + ': ' + fmt(a.dist_estrada_m, 0) + ' m').addTo(layers.acesso);
      });
      // selected points
      D.selecionados.forEach(p => {
        const on = visivel(p);
        L.circleMarker([p.lat, p.lon], { pane: 'sel', renderer: svgSel, radius: on ? 7 : 5, weight: 2, color: on ? '#111' : '#888',
          fillColor: TIPO[p.tipo], fillOpacity: on ? 0.95 : 0.35 })
          .bindPopup(popupSel(p)).addTo(layers.sel);
        if (on) {
          L.marker([p.lat, p.lon], { pane: 'num', interactive: false,
            icon: L.divIcon({ className: '', html: '<div class="fc-num">' + p.ordem + '</div>', iconSize: [20, 20], iconAnchor: [-4, 22] }) }).addTo(layers.num);
        }
      });
      ['pontos', 'sel', 'rotas', 'acesso', 'num'].forEach(k => {
        const cb = document.getElementById('fc-lyr-' + k);
        if (cb.checked) layers[k].addTo(map); else map.removeLayer(layers[k]);
      });
      legendPontos();
      roteiro();
      resumoSel();
    }

    function popupSel(p) {
      return '<strong>' + p.id + '</strong><br>Campaign ' + p.campanha + ' · Day ' + p.dia + ' · Stop ' + p.ordem + '<br>' +
        'Stratum: ' + p.estrato + ' (' + p.tipo + ')<br>Mean score: ' + fmt(p.score, 2) + ' · CVP 2025: ' + p.cvp + '<br>' +
        'Weight: ' + fmt(p.peso, 2) + ' (N = ' + p.N + ')<br>From previous stop: ' + fmt(p.km_ant) + ' km · ' + fmt(p.h_ant, 2) + ' h<br>' +
        'Distance to road: ' + fmt(p.dist_estrada, 0) + ' m' + (p.alerta ? '<br><strong>Access alert:</strong> ' + p.alerta : '');
    }

    function legendPontos() {
      const cfg = state.colorBy === 'classe' ? CLASSE : CVP;
      document.getElementById('fc-legend-pontos').innerHTML = Object.values(cfg)
        .map(x => '<span><span class="fc-sw" style="background:' + x.c + '"></span>' + x.l + '</span>').join('');
    }

    function roteiro() {
      const rows = D.selecionados.filter(visivel).sort((a, b) => a.campanha - b.campanha || a.dia - b.dia || a.ordem - b.ordem);
      document.getElementById('fc-roteiro-title').textContent = 'Itinerary · ' +
        (state.camp ? 'Campaign ' + state.camp + (state.dia ? ' · Day ' + state.dia : ' · all days') : 'both campaigns') + ' (' + rows.length + ' points)';
      document.getElementById('fc-roteiro').innerHTML =
        '<thead><tr><th>Camp.</th><th>Day</th><th class="n">Stop</th><th>Point</th><th>Stratum</th><th class="n">km from prev.</th><th class="n">h day</th><th class="n">Road dist. (m)</th></tr></thead><tbody>' +
        rows.map(p => '<tr class="fc-click" data-id="' + p.id + '"><td>' + p.campanha + '</td><td>' + p.dia + '</td><td class="n">' + p.ordem + '</td><td>' + p.id +
          '</td><td><span class="fc-sw" style="background:' + TIPO[p.tipo] + ';vertical-align:-1px;margin-right:5px"></span>' + p.estrato + '</td><td class="n">' + fmt(p.km_ant) +
          '</td><td class="n">' + fmt(p.h_dia) + '</td><td class="n">' + fmt(p.dist_estrada, 0) + (p.alerta ? ' ⚠' : '') + '</td></tr>').join('') + '</tbody>';
      document.querySelectorAll('#fc-roteiro tr.fc-click').forEach(tr => tr.addEventListener('click', () => {
        const p = selById[tr.dataset.id];
        map.setView([p.lat, p.lon], 13);
        L.popup().setLatLng([p.lat, p.lon]).setContent(popupSel(p)).openOn(map);
        mapEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }));
    }

    function resumoSel() {
      const el = document.getElementById('fc-resumo-sel');
      if (!state.camp) {
        el.innerHTML = D.resumo.map(c => '<div style="margin-top:0.35rem"><span class="fc-sw fc-sw--line" style="display:inline-block;vertical-align:2px;margin-right:6px;background:' + CAMP[c.campanha] + '"></span><strong>Campaign ' + c.campanha + ':</strong> ' +
          c.pontos + ' points · ' + c.dias + ' days · ' + fmt(c.km, 0) + ' km · ' + fmt(c.horas_viagem) + ' h driving · ' + fmt(c.horas_total) + ' h total</div>').join('');
        return;
      }
      const c = D.resumo.find(x => x.campanha === state.camp);
      let h = '<strong>Campaign ' + c.campanha + ':</strong> ' + c.pontos + ' points · ' + c.dias + ' days · ' + fmt(c.km, 0) + ' km · ' + fmt(c.horas_total) + ' h total';
      if (state.dia) {
        const rs = D.rotas.filter(visivel);
        const km = rs.reduce((s, r) => s + (r.km || 0), 0), hv = rs.reduce((s, r) => s + (r.horas_viagem || 0), 0);
        const d = D.dias.find(x => x.campanha === state.camp && x.dia === state.dia);
        h += '<div style="margin-top:0.35rem"><strong>Day ' + state.dia + ':</strong> ' + d.pontos + ' points · ' + fmt(km) + ' km · ' + fmt(hv) + ' h driving · ' + fmt(d.h) + ' h total</div>';
      }
      el.innerHTML = h;
    }

    function fit() {
      const pts = D.selecionados.filter(visivel).map(p => [p.lat, p.lon]);
      if (state.camp && !state.dia) pts.push([D.base.lat, D.base.lon]);
      if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.1));
    }

    // controls
    document.querySelectorAll('[data-fccolor]').forEach(b => b.addEventListener('click', () => {
      state.colorBy = b.dataset.fccolor;
      document.querySelectorAll('[data-fccolor]').forEach(x => x.classList.toggle('active', x === b));
      draw();
    }));
    ['pontos', 'sel', 'rotas', 'acesso', 'num'].forEach(k => document.getElementById('fc-lyr-' + k).addEventListener('change', draw));

    function buildDias() {
      const wrap = document.getElementById('fc-dia-wrap'), el = document.getElementById('fc-dia');
      wrap.style.display = state.camp ? '' : 'none';
      el.innerHTML = '';
      if (!state.camp) return;
      const dias = D.dias.filter(d => d.campanha === state.camp).map(d => d.dia);
      [0].concat(dias).forEach(d => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'fc-chip' + (d === state.dia ? ' active' : '');
        b.textContent = d ? 'Day ' + d : 'All days';
        b.addEventListener('click', () => {
          state.dia = d;
          el.querySelectorAll('.fc-chip').forEach(x => x.classList.toggle('active', x === b));
          draw(); fit();
        });
        el.appendChild(b);
      });
    }
    document.querySelectorAll('[data-camp]').forEach(b => b.addEventListener('click', () => {
      state.camp = +b.dataset.camp; state.dia = 0;
      document.querySelectorAll('[data-camp]').forEach(x => x.classList.toggle('active', x === b));
      buildDias(); draw(); fit();
    }));
    document.getElementById('fc-reset').addEventListener('click', fit);

    draw();
    fit();
  });
})();
