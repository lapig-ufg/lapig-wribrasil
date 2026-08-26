# Improve Pasture Mapping in the Cerrado Biome

Institutional repository containing data, high-performance analytical pipelines (DuckDB / Python), and an interactive web platform developed under the agreement between **WRI Brasil** and **FUNAPE**, with technical execution by **LAPIG/UFG** in cooperation with **Embrapa Cenargen** (**Project GR000153-73077-CARGILL-BRAZIL**).

Deliverable: **Product 1 — Detailed Sampling Plan and Sampling Improvement Strategies** (August 17, 2026).

---

## 📊 Summary of Datasets & Sample Series

The platform integrates **62,009 candidate samples** (in 2025) across a multi-year historical series (2020 to 2025), matched via **64-dimensional L2-renormalized cosine similarity** against Embrapa's **701 in situ reference polygons** (~1 ha; 608 classified across 7 pasture condition categories + 93 unlabeled):

| Sample Series | Description & Stratification | Samples / Year (2025) | Provenance & Nature |
| :--- | :--- | :--- | :--- |
| **50k Series** | Stratified random sampling from persistent pasture (2020–2025) | **50,000** | Proportional to 2025 vigor strata: Low (~35%), Medium (~44%), High (~21%) |
| **12k Series** | MapBiomas Col. 4 S2 (5,453) + MapBiomas 85k Landsat validation (6,556) | **12,009** | Visual inspection pasture samples & interpreted validation subset |
| **Total Candidates** | Inclusive universe before similarity, SOM, and CBERS-4A filters | **62,009** | Scenarios: Inclusive (62,009) vs. Agreement with Col. 11 (56,952) |
| **Embrapa Reference** | In situ field reference polygons (~1 ha) | **701** | 608 classified across 7 categories + 93 unclassified |

### Annual Breakdown of the 12k Series:
* **2019**: 12,483 points
* **2020**: 12,386 points
* **2021**: 12,281 points
* **2022**: 12,149 points
* **2023**: 12,080 points
* **2024**: 12,034 points
* **2025**: 12,009 points

---

## 🌐 Interactive Web Platform (`docs/`)

Built upon a lightweight, modular static architecture (compatible with Jekyll and GitHub Pages Source: `/docs`) featuring browser GPU acceleration via **Leaflet Canvas Markers** and dynamic charts via **Chart.js**:

* **Home Page (`/`)**: Institutional overview, objectives, key figures, and section navigation.
* **Md3 Analysis (`/analise-top3/`)**:
  * **Unified Filter Panel**: Instant switching between the **50k Series** and the **12k Series**, year selection (2019 to 2025), pasture vigor filtering (CVP 1, 2, 3), Md3 similarity thresholds (0.00 to 0.95), full-text search, and typology checkboxes.
  * **Spatial Bounding Box Selection**: Tool to interactively select any custom geographic bounding box across the Cerrado, automatically updating counters, charts, and sample inspection tables.
  * **Synchronized Dual Charts**: Chart 1 (Dynamic MapBiomas sample distribution in the active view) and Chart 2 (Fixed distribution of Embrapa's 701 ground-truth points).
  * **Detailed Table**: Inspection of Top-3 dot products, reference FIDs, target coordinates, and assigned typologies.
  * **Static Deliverables**: Direct downloads of technical Reports, Presentation decks, GEE Assets, Python scripts, and Open Data tables in Parquet, CSV, and JSON formats.
  * **SOM (Self-Organizing Maps)**: Section dedicated to unsupervised topological neural network clustering.

---

## 📁 Repository Directory Structure

```
lapig-wribrasil/
│
├── 🌐 docs/                          # Web Platform (Jekyll / GitHub Pages: /docs)
│   ├── _config.yml                  # Central Jekyll configuration (baseurl: "/lapig-wribrasil")
│   ├── _layouts/                    # Base layouts (default.html, page.html)
│   ├── _includes/                   # Modular HTML includes (map_viz, Produtos_Estaticos, etc.)
│   ├── assets/                      # Stylesheets, JavaScript engine, and JSON/CSV datasets
│   ├── material_suplementar/        # Technical Report (PDF) & Presentation (PDF)
│   ├── analise-top3/                # Md3 Analysis & Deliverables page
│   ├── comparacao/                  # Scenario comparison page
│   └── index.html                   # Homepage
│
├── 📊 dados/                         # Data Pipelines & Processing Engine
│   ├── arquivos_base/               # Raw Sentinel-2 embeddings, Embrapa points, MapBiomas inputs
│   ├── arquivos_saida/              # Processed Top-3 Parquets (50k & 12k Series · 2019–2025)
│   └── scripts/                     # Python / DuckDB processing pipelines
│
├── 📁 documentos/                    # Reports, Slide Decks, QGIS Styles & Maintenance Guides
│   ├── Report_Product_1_*.pdf       # Technical Report PDF
│   ├── Scaling_Ground_Truth_*.pdf   # Executive Presentation PDF
│   ├── campo_md3.pptx               # Field Presentation Deck
│   ├── qgis_cores.qml               # QGIS layer styling palette
│   └── procedimentos_manutencao/    # Maintenance & configuration documentation
│
├── 🛠️ servidor_local.py              # Local testing server (serves docs/ in real time)
├── 📄 LICENSE                       # Creative Commons Attribution 4.0 (CC BY 4.0)
└── 📘 README.md                      # Repository presentation and documentation
```

---

## 🚀 How to Run the Local Server

To preview the web platform locally in real time:

```bash
python servidor_local.py
```

Open in your browser: **`http://localhost:8000`** or **`http://localhost:8000/analise-top3/`**.

---

## 🛠️ Reproducing Data Pipelines

### 1. Generate Top-3 Tables for the 50k Series (2019–2025)
```bash
python dados/scripts/gerar_top3_pivotada_50k.py --year all
```

### 2. Generate Top-3 Tables for the 12k Series (2019–2025)
```bash
python dados/scripts/gerar_top3_pivotada_11k.py --year all
```

### 3. Update Embrapa Reference Dataset (701 Points)
```bash
python dados/scripts/exportar_referencia_embrapa.py
```

---

## 🌿 Canonical Pasture Typologies (Embrapa)

Ground-truth samples and spectral similarity predictions are categorized into 7 primary classes:
1. **Productive Pasture** (`#faea40`): Well-managed pasture with high forage biomass.
2. **Pasture with Weeds** (`#d8ff6c`): Infestation of herbaceous/ruderal invasive plants.
3. **Pasture with Shrubs / Woody Species** (`#66c600`): Significant presence of shrub and tree canopy layers.
4. **Intermediate Pasture** (`#f4b346`): Moderate vegetative vigor with mixed grass and soil coverage.
5. **Biological Degradation** (`#813209`): Severe degradation with prominent bare soil.
6. **Natural Regeneration** (`#0e5f0e`): Areas undergoing natural recovery of native Cerrado vegetation.
7. **Miscellaneous** (`#ec2b10`): Atypical, transitional, or mixed land-use features.

---

## 🤝 Partner Institutions
* **LAPIG / UFG** — Image Processing and Geoprocessing Laboratory (Federal University of Goiás)
* **WRI Brasil** — World Resources Institute Brasil
* **Embrapa** — Brazilian Agricultural Research Corporation

---

## 📄 License

This work, including all code, datasets, documentation, and web assets, is licensed under a **[Creative Commons Attribution 4.0 International License (CC BY 4.0)](file:///C:/Users/windows/Documents/github/WRI_LAPIG/LICENSE)**.
