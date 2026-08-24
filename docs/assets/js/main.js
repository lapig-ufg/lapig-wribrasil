// Intersection Observer for scroll-triggered animations
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

// Smooth active nav highlight
const sections = document.querySelectorAll('[id]');
const navLinks = document.querySelectorAll('.site-nav__links a');

window.addEventListener('scroll', () => {
  let current = '';
  sections.forEach(section => {
    const sectionTop = section.offsetTop - 100;
    if (scrollY >= sectionTop) {
      current = section.getAttribute('id');
    }
  });
  navLinks.forEach(link => {
    link.style.color = link.getAttribute('href') === '#' + current
      ? 'var(--color-accent)' : '';
  });
});

// ──────────────────────────────────────────────────────────
//  INTERACTIVE MAP — Md3 Series (50k & 12k) MapBiomas × Embrapa
// ──────────────────────────────────────────────────────────
(function () {
  'use strict';

  // Guard: only run on pages that have the map container
  const mapEl = document.getElementById('map-amostras');
  if (!mapEl) return;

  // 1. Tipologia color palette (Embrapa official schema with English labels)
  const TIPOLOGIA_CONFIG = {
    'PASTO PRODUTIVO': { color: '#faea40', label: 'Productive Pasture' },
    'PASTO COM ERVAS': { color: '#d8ff6c', label: 'Pasture with Weeds' },
    'PASTO COM LENHOSAS': { color: '#66c600', label: 'Pasture with Shrubs / Trees' },
    'INTERMEDIARIO': { color: '#f4b346', label: 'Intermediate Pasture' },
    'DEG BIOLOGICA': { color: '#813209', label: 'Biological Degradation' },
    'REG NATURAL': { color: '#0e5f0e', label: 'Natural Regeneration' },
    'MISCELANEA': { color: '#ec2b10', label: 'Miscellaneous' },
    'Outros': { color: '#888888', label: 'Other' }
  };

  const TIPOLOGIA_ORDER = [
    'PASTO PRODUTIVO', 'PASTO COM ERVAS', 'PASTO COM LENHOSAS',
    'INTERMEDIARIO', 'DEG BIOLOGICA', 'REG NATURAL', 'MISCELANEA'
  ];

  // Default view: Cerrado / Central Brazil
  const BRAZIL_CENTER = [-15.5, -49.5];
  const BRAZIL_ZOOM = 6;

  // GPU-Accelerated Canvas Renderer for high-throughput markers
  const canvasRenderer = L.canvas({ padding: 0.5 });

  // Initialize Leaflet map
  const map = L.map('map-amostras', {
    center: BRAZIL_CENTER,
    zoom: BRAZIL_ZOOM,
    scrollWheelZoom: true,
    zoomControl: true,
    preferCanvas: true
  });

  // CartoDB Voyager basemap
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · ' +
      '<a href="https://carto.com/attributions">CARTO</a> · LAPIG/UFG · WRI Brasil',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(map);

  // In-Memory Cache
  const DATA_CACHE = {};

  // State
  let currentDataset = '50k'; // '50k' or '12k'
  let currentYear = '2025';
  let allData = [];
  let filteredData = [];
  let activeClasses = new Set(TIPOLOGIA_ORDER);
  let activeVigors = new Set([1, 2, 3]);
  let minMd3Threshold = 0.00;
  let searchQuery = '';
  let currentBBox = null; // { minLat, maxLat, minLng, maxLng }

  // Layer Groups
  const markerGroup = L.featureGroup().addTo(map);
  const embrapaLayerGroup = L.layerGroup();
  let showEmbrapaLayer = false;
  let activeRectangleLayer = null;
  let isDrawingRect = false;

  // Charts
  let chartMapBiomas = null;
  let chartEmbrapa = null;
  let embrapaRefData = null;

  // Debounce helper
  let searchDebounceTimeout = null;

  // ── 0. Dataset Selector (50k vs 12k) ──
  function setupDatasetSelector() {
    const btn50k = document.getElementById('btn-dataset-50k');
    const btn12k = document.getElementById('btn-dataset-12k') || document.getElementById('btn-dataset-11k');
    const yearFilterTitle = document.getElementById('year-filter-title');

    if (btn50k && btn12k) {
      btn50k.addEventListener('click', () => {
        if (currentDataset === '50k') return;
        currentDataset = '50k';
        btn50k.classList.add('active');
        btn12k.classList.remove('active');
        if (yearFilterTitle) yearFilterTitle.textContent = '📅 Analysis Year (50k Series · 50,000 pts)';
        loadMd3Year(currentYear);
      });

      btn12k.addEventListener('click', () => {
        if (currentDataset === '12k') return;
        currentDataset = '12k';
        btn12k.classList.add('active');
        btn50k.classList.remove('active');
        if (yearFilterTitle) yearFilterTitle.textContent = '📅 Analysis Year (12k Series · 12,395 pts)';
        loadMd3Year(currentYear);
      });
    }
  }

  // ── 1. Accordion Toggle ──
  function setupAccordion() {
    document.querySelectorAll('.filter-item__header').forEach(header => {
      header.addEventListener('click', () => {
        const item = header.closest('.filter-item');
        if (item) {
          item.classList.toggle('open');
        }
      });
    });
  }

  // ── 2. Build Filter Checkboxes (Typologies) ──
  function buildFilters() {
    const filterList = document.getElementById('filter-list');
    if (!filterList) return;
    filterList.innerHTML = '';

    TIPOLOGIA_ORDER.forEach(tip => {
      const cfg = TIPOLOGIA_CONFIG[tip];
      const li = document.createElement('li');
      const isChecked = activeClasses.has(tip);
      li.innerHTML = `
        <input type="checkbox" id="filter-${tip.replace(/\s+/g, '_')}" ${isChecked ? 'checked' : ''} data-class="${tip}">
        <span class="filter-swatch" style="background:${cfg.color}"></span>
        <span title="${cfg.label}">${cfg.label}</span>
        <span class="filter-count" id="count-${tip.replace(/\s+/g, '_')}">0</span>
      `;
      li.querySelector('input').addEventListener('change', onClassFilterChange);
      filterList.appendChild(li);
    });

    updateToggleAllButton();
  }

  function updateToggleAllButton() {
    const btn = document.getElementById('btn-toggle-all');
    if (!btn) return;
    if (activeClasses.size === 0) {
      btn.textContent = 'Select All';
    } else {
      btn.textContent = 'Deselect All';
    }
  }

  function setupToggleAll() {
    const btn = document.getElementById('btn-toggle-all');
    if (!btn) return;
    btn.onclick = function () {
      if (activeClasses.size === 0) {
        TIPOLOGIA_ORDER.forEach(t => activeClasses.add(t));
      } else {
        activeClasses.clear();
      }
      syncFilterCheckboxes();
      updateToggleAllButton();
      applyFilters();
    };
  }

  function syncFilterCheckboxes() {
    TIPOLOGIA_ORDER.forEach(tip => {
      const cb = document.getElementById('filter-' + tip.replace(/\s+/g, '_'));
      if (cb) cb.checked = activeClasses.has(tip);
    });
  }

  function onClassFilterChange(e) {
    const cls = e.target.getAttribute('data-class');
    if (e.target.checked) {
      activeClasses.add(cls);
    } else {
      activeClasses.delete(cls);
    }
    updateToggleAllButton();
    applyFilters();
  }

  // ── 3. Vigor (CVP) Filter Handlers ──
  function setupVigorFilters() {
    document.querySelectorAll('.vigor-checkbox').forEach(cb => {
      cb.addEventListener('change', (e) => {
        const val = parseInt(e.target.value, 10);
        if (e.target.checked) {
          activeVigors.add(val);
        } else {
          activeVigors.delete(val);
        }
        applyFilters();
      });
    });
  }

  // ── 4. Md3 Slider & Quick Chips Handlers ──
  function setupMd3Filters() {
    const slider = document.getElementById('md3-slider');
    const display = document.getElementById('md3-val-display');
    const chips = document.querySelectorAll('.md3-chip');

    if (slider) {
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        minMd3Threshold = val;
        if (display) {
          display.textContent = val === 0 ? 'Md3 ≥ 0.00' : `Md3 ≥ ${val.toFixed(2)}`;
        }
        chips.forEach(c => {
          c.classList.toggle('active', parseFloat(c.getAttribute('data-val')) === val);
        });
        applyFilters();
      });
    }

    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const val = parseFloat(chip.getAttribute('data-val'));
        minMd3Threshold = val;
        if (slider) slider.value = val;
        if (display) {
          display.textContent = val === 0 ? 'Md3 ≥ 0.00' : `Md3 ≥ ${val.toFixed(2)}`;
        }
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        applyFilters();
      });
    });
  }

  // ── 5. Year Selector Radio Chips ──
  function setupYearSelector() {
    document.querySelectorAll('.year-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const radio = chip.querySelector('input[type="radio"]');
        if (radio && radio.value !== currentYear) {
          document.querySelectorAll('.year-chip').forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          radio.checked = true;
          loadMd3Year(radio.value);
        }
      });
    });
  }

  // ── 6. Rectangle Selection Tool ──
  function setupRectangleDrawTool() {
    const btnDraw = document.getElementById('btn-draw-rect');
    const btnClear = document.getElementById('btn-clear-rect');
    const hint = document.getElementById('map-selection-hint');

    if (!btnDraw) return;

    let startLatLng = null;
    let tempRect = null;

    function onMouseDown(e) {
      if (!isDrawingRect) return;
      startLatLng = e.latlng;
      map.dragging.disable();

      if (tempRect) {
        map.removeLayer(tempRect);
        tempRect = null;
      }

      tempRect = L.rectangle([startLatLng, startLatLng], {
        color: '#129912',
        weight: 2,
        dashArray: '5, 5',
        fillColor: '#129912',
        fillOpacity: 0.15
      }).addTo(map);

      map.on('mousemove', onMouseMove);
      map.on('mouseup', onMouseUp);
    }

    function onMouseMove(e) {
      if (!isDrawingRect || !startLatLng || !tempRect) return;
      const bounds = L.latLngBounds(startLatLng, e.latlng);
      tempRect.setBounds(bounds);
    }

    function onMouseUp(e) {
      if (!isDrawingRect || !startLatLng || !tempRect) return;
      map.off('mousemove', onMouseMove);
      map.off('mouseup', onMouseUp);
      map.dragging.enable();

      const bounds = tempRect.getBounds();

      // If rectangle is too small (accidental click), dismiss
      if (bounds.getNorth() === bounds.getSouth() && bounds.getEast() === bounds.getWest()) {
        map.removeLayer(tempRect);
        tempRect = null;
        return;
      }

      if (activeRectangleLayer) {
        map.removeLayer(activeRectangleLayer);
      }
      activeRectangleLayer = tempRect;
      tempRect = null;

      currentBBox = {
        minLat: bounds.getSouth(),
        maxLat: bounds.getNorth(),
        minLng: bounds.getWest(),
        maxLng: bounds.getEast()
      };

      // Turn off drawing mode
      isDrawingRect = false;
      btnDraw.classList.remove('active');
      mapEl.style.cursor = '';
      if (hint) hint.style.display = 'none';
      if (btnClear) btnClear.style.display = 'inline-flex';

      applyFilters();
    }

    btnDraw.addEventListener('click', () => {
      isDrawingRect = !isDrawingRect;
      if (isDrawingRect) {
        btnDraw.classList.add('active');
        mapEl.style.cursor = 'crosshair';
        if (hint) hint.style.display = 'block';
        map.on('mousedown', onMouseDown);
      } else {
        btnDraw.classList.remove('active');
        mapEl.style.cursor = '';
        if (hint) hint.style.display = 'none';
        map.off('mousedown', onMouseDown);
      }
    });

    if (btnClear) {
      btnClear.addEventListener('click', () => {
        if (activeRectangleLayer) {
          map.removeLayer(activeRectangleLayer);
          activeRectangleLayer = null;
        }
        currentBBox = null;
        btnClear.style.display = 'none';
        applyFilters();
      });
    }
  }

  // ── 7. Embrapa 701 Ground-Truth Layer Toggle ──
  function setupEmbrapaLayerToggle() {
    const btn = document.getElementById('btn-toggle-embrapa');
    if (!btn) return;

    btn.addEventListener('click', () => {
      showEmbrapaLayer = !showEmbrapaLayer;
      btn.classList.toggle('active', showEmbrapaLayer);

      if (showEmbrapaLayer) {
        if (!map.hasLayer(embrapaLayerGroup)) {
          map.addLayer(embrapaLayerGroup);
        }
        loadAndRenderEmbrapaMarkers();
      } else {
        if (map.hasLayer(embrapaLayerGroup)) {
          map.removeLayer(embrapaLayerGroup);
        }
      }
    });
  }

  function loadAndRenderEmbrapaMarkers() {
    if (embrapaLayerGroup.getLayers().length > 0) return;

    const url = (window.siteBaseUrl || '') + '/assets/embrapa_referencia.json';
    fetch(url)
      .then(res => res.json())
      .then(payload => {
        embrapaRefData = payload;
        renderEmbrapaReferenceChart(payload.distribuicao);

        if (payload.pontos && Array.isArray(payload.pontos)) {
          payload.pontos.forEach(pt => {
            const cfg = TIPOLOGIA_CONFIG[pt.classe] || { color: '#1e3a8a', label: pt.classe };

            const marker = L.circleMarker([pt.lat, pt.lon], {
              renderer: canvasRenderer,
              radius: 5.5,
              fillColor: cfg.color,
              color: '#000000',
              weight: 2,
              opacity: 0.9,
              fillOpacity: 1.0
            });

            marker.bindPopup(`
              <div class="popup-box" style="font-family: var(--font-sans); font-size: 0.8rem; min-width: 200px;">
                <div style="font-weight: 700; color: #1e3a8a; border-bottom: 1px solid #ddd; padding-bottom: 3px; margin-bottom: 6px;">
                  📍 Field Reference (Ground Truth)
                </div>
                <div><strong>Target FID:</strong> #${pt.fid}</div>
                <div><strong>Typology:</strong> <span style="display:inline-flex; align-items: center; padding: 2px 7px; border-radius: 4px; background: ${cfg.color}35; color: #000000; font-weight: 700; border: 1px solid ${cfg.color};"><span style="display:inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${cfg.color}; margin-right: 5px; border: 1px solid rgba(0,0,0,0.25);"></span>${cfg.label}</span></div>
                <div style="font-size: 0.72rem; color: #444; margin-top: 4px;"><strong>Coords:</strong> ${pt.lat.toFixed(4)}, ${pt.lon.toFixed(4)}</div>
              </div>
            `);

            embrapaLayerGroup.addLayer(marker);
          });
        }
      })
      .catch(err => console.warn('Could not load ground-truth points:', err));
  }

  // ── 8. Multi-Criteria Filter Engine ──
  function applyFilters() {
    filteredData = allData.filter(pt => {
      // 1. Tipologia filter
      if (!activeClasses.has(pt.classe)) return false;

      // 2. Vigor filter (1, 2, 3)
      if (activeVigors.size > 0 && !activeVigors.has(pt.cvp)) return false;

      // 3. Md3 minimum threshold
      if (pt.md3 < minMd3Threshold) return false;

      // 4. Spatial rectangle bounding box filter
      if (currentBBox) {
        if (pt.lat < currentBBox.minLat || pt.lat > currentBBox.maxLat ||
          pt.lng < currentBBox.minLng || pt.lng > currentBBox.maxLng) {
          return false;
        }
      }

      // 5. Search query
      if (searchQuery) {
        const matchesId = String(pt.id).includes(searchQuery);
        const matchesFid = String(pt.target_fid_1).includes(searchQuery);
        const cfg = TIPOLOGIA_CONFIG[pt.classe];
        const matchesClass = pt.classe.toLowerCase().includes(searchQuery) || (cfg && cfg.label.toLowerCase().includes(searchQuery));
        const matchesLoc = (pt.loc_1 || '').toLowerCase().includes(searchQuery);
        if (!matchesId && !matchesFid && !matchesClass && !matchesLoc) return false;
      }

      return true;
    });

    renderCanvasMarkers();
    updateCounterAndStats();
    updateMapBiomasChart();
    showOverlapTable(filteredData);
    updateActiveFilterBadge();
  }

  // ── 9. Render Canvas Markers ──
  function renderCanvasMarkers() {
    markerGroup.clearLayers();

    filteredData.forEach(pt => {
      const cfg = TIPOLOGIA_CONFIG[pt.classe] || { color: '#888888', label: pt.classe };

      const marker = L.circleMarker([pt.lat, pt.lng], {
        renderer: canvasRenderer,
        radius: 3.5,
        fillColor: cfg.color,
        color: '#1a1a1a',
        weight: 0.5,
        opacity: 0.8,
        fillOpacity: 0.85
      });

      marker.bindPopup(() => getPopupContent(pt, cfg));
      markerGroup.addLayer(marker);
    });
  }

  function getPopupContent(pt, cfg) {
    const vigorLabels = { 1: 'Vigor 1 (High)', 2: 'Vigor 2 (Medium)', 3: 'Vigor 3 (Low)' };
    const vigorStr = vigorLabels[pt.cvp] || `Vigor ${pt.cvp}`;

    return `
      <div class="popup-box" style="font-family: var(--font-sans); font-size: 0.82rem; line-height: 1.4; min-width: 220px;">
        <div style="font-weight: 700; font-size: 0.88rem; color: #1a1a1a; margin-bottom: 4px;">
          MapBiomas Sample #${pt.id}
        </div>
        <div style="margin-bottom: 6px;">
          <span style="display:inline-flex; align-items: center; padding: 2px 7px; border-radius: 4px; background: ${cfg.color}35; color: #000000; font-weight: 700; border: 1px solid ${cfg.color};">
            <span style="display:inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${cfg.color}; margin-right: 5px; border: 1px solid rgba(0,0,0,0.25);"></span>
            ${cfg.label}
          </span>
          <span class="vigor-tag vigor-${pt.cvp}" style="margin-left: 4px;">${vigorStr}</span>
        </div>
        <div style="margin-top: 6px; line-height: 1.4; color: #111111;">
          <strong>Target Coords:</strong> ${pt.lat.toFixed(4)}, ${pt.lng.toFixed(4)}<br>
          <strong>Reference Match:</strong> FID #${pt.target_fid_1} (${(pt.prod_escalar_1 || 0).toFixed(3)})<br>
          <strong>Mean Md3:</strong> ${(pt.md3 || 0).toFixed(3)}<br>
          <strong>Reference Loc:</strong> ${pt.loc_1 || '—'}
        </div>
      </div>
    `;
  }

  // ── 10. Update Counter, Filter Badge and Counts ──
  function updateCounterAndStats() {
    const countNumberEl = document.getElementById('counter-number');
    const countLabelEl = document.getElementById('counter-label');
    const countSubEl = document.getElementById('counter-sub');
    const chartTitleEl = document.getElementById('chart-title');

    const total = allData.length || (currentDataset === '50k' ? 50000 : 12009);
    const current = filteredData.length;
    const pct = total > 0 ? ((current / total) * 100).toFixed(1) : '100';
    const seriesLabel = currentDataset === '50k' ? '50k Series' : '12k Series';

    if (countNumberEl) countNumberEl.textContent = current.toLocaleString('en-US');
    if (countLabelEl) countLabelEl.textContent = `MapBiomas Samples (${seriesLabel} · Year ${currentYear})`;
    if (chartTitleEl) chartTitleEl.textContent = `MapBiomas Sample Distribution (${seriesLabel})`;
    if (countSubEl) {
      if (currentBBox) {
        countSubEl.textContent = `${pct}% of points (Custom Bounding Box Selection)`;
      } else {
        countSubEl.textContent = `${pct}% of visible points`;
      }
    }

    // Update counts per typology in filter checkboxes
    const countsByClass = {};
    filteredData.forEach(pt => {
      countsByClass[pt.classe] = (countsByClass[pt.classe] || 0) + 1;
    });

    TIPOLOGIA_ORDER.forEach(tip => {
      const span = document.getElementById('count-' + tip.replace(/\s+/g, '_'));
      if (span) {
        span.textContent = (countsByClass[tip] || 0).toLocaleString('en-US');
      }
    });
  }

  function updateActiveFilterBadge() {
    const badge = document.getElementById('active-filters-count');
    if (!badge) return;

    let activeFilterCount = 0;
    if (currentDataset !== '50k') activeFilterCount++;
    if (activeClasses.size < TIPOLOGIA_ORDER.length) activeFilterCount++;
    if (activeVigors.size < 3) activeFilterCount++;
    if (minMd3Threshold > 0) activeFilterCount++;
    if (searchQuery) activeFilterCount++;
    if (currentBBox) activeFilterCount++;

    if (activeFilterCount === 0) {
      badge.textContent = 'Default';
      badge.style.background = 'var(--color-accent-glow)';
    } else {
      badge.textContent = `${activeFilterCount} Active`;
      badge.style.background = '#fef08a';
    }
  }

  // ── 11. Dual Charts: MapBiomas & Embrapa Reference ──
  function updateMapBiomasChart() {
    const canvas = document.getElementById('chart-classes');
    if (!canvas) return;

    const counts = {};
    TIPOLOGIA_ORDER.forEach(tip => { counts[tip] = 0; });
    filteredData.forEach(pt => {
      if (counts[pt.classe] !== undefined) {
        counts[pt.classe]++;
      }
    });

    const labels = TIPOLOGIA_ORDER.map(t => TIPOLOGIA_CONFIG[t].label);
    const dataValues = TIPOLOGIA_ORDER.map(t => counts[t]);
    const bgColors = TIPOLOGIA_ORDER.map(t => TIPOLOGIA_CONFIG[t].color);

    if (!chartMapBiomas) {
      const ctx = canvas.getContext('2d');
      chartMapBiomas = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            data: dataValues,
            backgroundColor: bgColors,
            borderRadius: 4,
            borderWidth: 1,
            borderColor: 'rgba(0,0,0,0.1)'
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  const val = ctx.parsed.x || 0;
                  const total = filteredData.length || 1;
                  const pct = ((val / total) * 100).toFixed(1);
                  return `${val.toLocaleString('en-US')} points (${pct}%)`;
                }
              }
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(0,0,0,0.05)' },
              ticks: { font: { size: 9, family: 'Inter' } }
            },
            y: {
              grid: { display: false },
              ticks: { font: { size: 9, family: 'Inter' } }
            }
          }
        }
      });
    } else {
      chartMapBiomas.data.datasets[0].data = dataValues;
      chartMapBiomas.update();
    }
  }

  function renderEmbrapaReferenceChart(distribuicao) {
    const canvas = document.getElementById('chart-embrapa');
    if (!canvas || !distribuicao) return;

    const labels = TIPOLOGIA_ORDER.map(t => TIPOLOGIA_CONFIG[t].label);
    const dataValues = TIPOLOGIA_ORDER.map(t => (distribuicao[t] ? distribuicao[t].total : 0));
    const bgColors = TIPOLOGIA_ORDER.map(t => TIPOLOGIA_CONFIG[t].color);

    if (!chartEmbrapa) {
      const ctx = canvas.getContext('2d');
      chartEmbrapa = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            data: dataValues,
            backgroundColor: bgColors,
            borderRadius: 4,
            borderWidth: 1,
            borderColor: 'rgba(0,0,0,0.15)'
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  const val = ctx.parsed.x || 0;
                  const pct = ((val / 701) * 100).toFixed(1);
                  return `${val} field points (${pct}%)`;
                }
              }
            }
          },
          scales: {
            x: {
              grid: { color: 'rgba(0,0,0,0.05)' },
              ticks: { font: { size: 9, family: 'Inter' } }
            },
            y: {
              grid: { display: false },
              ticks: { font: { size: 9, family: 'Inter' } }
            }
          }
        }
      });
    } else {
      chartEmbrapa.data.datasets[0].data = dataValues;
      chartEmbrapa.update();
    }
  }

  // ── 12. Populate Details Table ──
  function showOverlapTable(points) {
    const container = document.getElementById('overlap-table-container');
    const thead = document.getElementById('overlap-thead');
    const tbody = document.getElementById('overlap-tbody');
    const countSpan = document.getElementById('table-count');
    if (!container || !thead || !tbody) return;

    if (points.length === 0) {
      container.style.display = 'none';
      return;
    }

    container.style.display = 'block';
    if (countSpan) countSpan.textContent = points.length.toLocaleString('en-US');

    tbody.innerHTML = '';

    const maxTableRows = 100;
    const rowsToDisplay = points.slice(0, maxTableRows);

    rowsToDisplay.forEach(pt => {
      const cfg = TIPOLOGIA_CONFIG[pt.classe] || { color: '#888888', label: pt.classe };
      const locAlvoStr = `${Number(pt.lat).toFixed(4)}, ${Number(pt.lng).toFixed(4)}`;

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>#${pt.id ?? '—'}</strong></td>
        <td><code>${locAlvoStr}</code></td>
        <td><span class="vigor-tag vigor-${pt.cvp || 1}">Vigor ${pt.cvp || 1}</span></td>
        <td>Target FID #${pt.target_fid_1 ?? '—'}</td>
        <td>
          <span class="class-tag" style="background-color: ${cfg.color}35; color: #000000; border: 1px solid ${cfg.color}; font-weight: 700;">
            <span style="display:inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${cfg.color}; margin-right: 5px; border: 1px solid rgba(0,0,0,0.25);"></span>
            ${cfg.label}
          </span>
        </td>
        <td><strong>${pt.prod_escalar_1 ? pt.prod_escalar_1.toFixed(3) : '—'}</strong></td>
        <td>${pt.md3 ? pt.md3.toFixed(3) : '—'}</td>
        <td>${pt.loc_1 || '—'}</td>
      `;
      tbody.appendChild(tr);
    });

    if (points.length > maxTableRows) {
      const trExtra = document.createElement('tr');
      trExtra.innerHTML = `
        <td colspan="8" style="text-align:center; color: var(--color-muted); font-style: italic; padding: 0.8rem;">
          ... and ${(points.length - maxTableRows).toLocaleString('en-US')} more matching samples (total filtered: ${points.length.toLocaleString('en-US')})
        </td>
      `;
      tbody.appendChild(trExtra);
    }
  }

  // ── 13. Load Md3 Dataset by Year & Dataset ──
  function loadMd3Year(year) {
    currentYear = year;
    const countNumberEl = document.getElementById('counter-number');
    const countLabelEl = document.getElementById('counter-label');
    const seriesLabel = currentDataset === '50k' ? '50k Series' : '12k Series';

    if (countNumberEl) countNumberEl.textContent = 'Loading...';
    if (countLabelEl) countLabelEl.textContent = `Loading ${seriesLabel} (${year})...`;

    const cacheKey = `${currentDataset}_${year}`;
    if (DATA_CACHE[cacheKey]) {
      allData = DATA_CACHE[cacheKey];
      applyFilters();
      return;
    }

    const url = `${window.siteBaseUrl || ''}/assets/tabela_top3_${currentDataset}_${year}.json`;

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(payload => {
        let parsed = [];
        if (payload.data && Array.isArray(payload.data)) {
          const tipList = payload.tipologias || TIPOLOGIA_ORDER;
          parsed = payload.data.map(row => {
            const t1Idx = row[3];
            const className = tipList[t1Idx] || 'Outros';
            return {
              id: row[0],
              lat: row[1],
              lng: row[2],
              classe: className,
              prod_escalar_1: row[4],
              target_fid_1: row[5],
              md3: row[6],
              loc_1: row[7],
              cvp: row[8] !== undefined ? row[8] : 1
            };
          });
        }

        DATA_CACHE[cacheKey] = parsed;
        allData = parsed;
        applyFilters();
      })
      .catch(err => {
        console.error('Error loading Md3 data:', err);
        if (countNumberEl) countNumberEl.textContent = 'Error';
        alert(`Could not load data for year "${year}" in ${seriesLabel}. Please verify that ${url} exists.`);
      });
  }

  // ── 14. Reset All Filters Button ──
  function setupClearFiltersButton() {
    const btnClearAll = document.getElementById('btn-clear-filters');
    const searchInput = document.getElementById('search-input');
    const md3Slider = document.getElementById('md3-slider');
    const md3Display = document.getElementById('md3-val-display');

    if (btnClearAll) {
      btnClearAll.addEventListener('click', () => {
        // Reset tipologias
        activeClasses = new Set(TIPOLOGIA_ORDER);
        syncFilterCheckboxes();
        updateToggleAllButton();

        // Reset vigors
        activeVigors = new Set([1, 2, 3]);
        document.querySelectorAll('.vigor-checkbox').forEach(cb => { cb.checked = true; });

        // Reset Md3 threshold
        minMd3Threshold = 0.00;
        if (md3Slider) md3Slider.value = 0.00;
        if (md3Display) md3Display.textContent = 'Md3 ≥ 0.00';
        document.querySelectorAll('.md3-chip').forEach(c => {
          c.classList.toggle('active', parseFloat(c.getAttribute('data-val')) === 0.00);
        });

        // Reset search
        searchQuery = '';
        if (searchInput) searchInput.value = '';

        // Reset spatial rectangle
        if (activeRectangleLayer) {
          map.removeLayer(activeRectangleLayer);
          activeRectangleLayer = null;
        }
        currentBBox = null;
        const btnClearRect = document.getElementById('btn-clear-rect');
        if (btnClearRect) btnClearRect.style.display = 'none';

        applyFilters();
      });
    }
  }

  // ── 15. Global Map Reset Button ──
  function setupMapResetButton() {
    const mapResetBtn = document.getElementById('map-reset');
    if (mapResetBtn) {
      mapResetBtn.addEventListener('click', function () {
        map.flyTo(BRAZIL_CENTER, BRAZIL_ZOOM, { duration: 0.8 });
      });
    }
  }

  // ── 16. Search Input Listener ──
  function setupSearchInput() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        clearTimeout(searchDebounceTimeout);
        searchDebounceTimeout = setTimeout(() => {
          searchQuery = e.target.value.trim().toLowerCase();
          applyFilters();
        }, 150);
      });
    }
  }

  // ── Initialization Sequence ──
  setupDatasetSelector();
  setupAccordion();
  buildFilters();
  setupToggleAll();
  setupVigorFilters();
  setupMd3Filters();
  setupYearSelector();
  setupRectangleDrawTool();
  setupEmbrapaLayerToggle();
  setupClearFiltersButton();
  setupMapResetButton();
  setupSearchInput();

  // Load Embrapa reference distribution for Chart 2 right away
  loadAndRenderEmbrapaMarkers();

  // Initial Load: 2025 MapBiomas 50k series
  loadMd3Year('2025');
})();

// ──────────────────────────────────────────────────────────
//  SPLIT MAP & CHARTS LOGIC
// ──────────────────────────────────────────────────────────
(function () {
  'use strict';

  // Guard: only run on pages that have the split-map container
  if (!document.getElementById('split-map')) return;

  const splitMap = L.map('split-map', {
    center: [-15.0, -49.0],
    zoom: 5,
    zoomControl: true,
    scrollWheelZoom: false
  });

  // Common Basemap (Background)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(splitMap);

  // Raster Layers for Comparison
  const leftLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    opacity: 0.6,
    attribution: 'Scenario A'
  }).addTo(splitMap);

  const rightLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    opacity: 0.6,
    attribution: 'Scenario B'
  }).addTo(splitMap);

  // Side-by-Side control
  L.control.sideBySide(leftLayer, rightLayer).addTo(splitMap);

  // Prevent accidental drag interference
  setTimeout(() => {
    const divider = document.querySelector('.leaflet-sbs-divider');
    if (divider) {
      const disableDrag = () => splitMap.dragging.disable();
      const enableDrag = () => splitMap.dragging.enable();

      divider.addEventListener('mousedown', disableDrag);
      divider.addEventListener('touchstart', disableDrag, { passive: true });

      document.addEventListener('mouseup', enableDrag);
      document.addEventListener('touchend', enableDrag);
    }
  }, 500);

  // Setup Comparison Charts
  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: function (context) {
            return context.parsed.y + '%';
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        grid: { color: 'rgba(0,0,0,0.05)' },
        ticks: { font: { size: 10 } }
      },
      x: {
        grid: { display: false },
        ticks: { font: { size: 10 } }
      }
    }
  };

  const canvasLeft = document.getElementById('chart-left');
  if (canvasLeft) {
    const ctxLeft = canvasLeft.getContext('2d');
    new Chart(ctxLeft, {
      type: 'bar',
      data: {
        labels: ['Forest', 'Pasture', 'Other'],
        datasets: [{
          data: [65, 25, 10],
          backgroundColor: ['#129912', '#ffd700', '#aaaaaa'],
          borderRadius: 4
        }]
      },
      options: commonOptions
    });
  }

  const canvasRight = document.getElementById('chart-right');
  if (canvasRight) {
    const ctxRight = canvasRight.getContext('2d');
    new Chart(ctxRight, {
      type: 'bar',
      data: {
        labels: ['Forest', 'Pasture', 'Other'],
        datasets: [{
          data: [40, 50, 10],
          backgroundColor: ['#129912', '#ffd700', '#aaaaaa'],
          borderRadius: 4
        }]
      },
      options: commonOptions
    });
  }
})();