"""
Exports class distribution and 701 field ground-truth points from Embrapa
from dados/arquivos_base/embeddings_embrapa_year_colet.parquet
to docs/assets/embrapa_referencia.json and CSV formats for download.
"""

import csv
import json
from pathlib import Path
import duckdb

DIR_SCRIPT = Path(__file__).resolve().parent
DIR_DADOS = DIR_SCRIPT.parent
DIR_ROOT = DIR_DADOS.parent

EMBRAPA_PARQUET = DIR_DADOS / "arquivos_base" / "embeddings_embrapa_year_colet.parquet"
OUT_JSON = DIR_ROOT / "docs" / "assets" / "embrapa_referencia.json"
OUT_CSV_DOCS = DIR_ROOT / "docs" / "assets" / "embrapa_referencia_701_pontos.csv"
OUT_CSV_BASE = DIR_DADOS / "arquivos_base" / "embrapa_referencia_701_pontos.csv"

TYPOLOGY_LABELS = {
    'PASTO PRODUTIVO': 'Productive Pasture',
    'PASTO COM ERVAS': 'Pasture with Weeds',
    'PASTO COM LENHOSAS': 'Pasture with Shrubs / Trees',
    'INTERMEDIARIO': 'Intermediate Pasture',
    'DEG BIOLOGICA': 'Biological Degradation',
    'REG NATURAL': 'Natural Regeneration',
    'MISCELANEA': 'Miscellaneous',
}


def export_embrapa_reference():
    if not EMBRAPA_PARQUET.exists():
        print(f"[ERROR] Embrapa reference parquet not found: {EMBRAPA_PARQUET}")
        return

    con = duckdb.connect()

    # 1. Static distribution by pasture condition class
    query_dist = f"""
        WITH padronizado AS (
            SELECT 
                TARGET_FID AS target_fid,
                latitude,
                longitude,
                COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_) AS tipologia_raw,
                CASE 
                    WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%PRODUTIVO%' THEN 'PASTO PRODUTIVO'
                    WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%ERVA%' THEN 'PASTO COM ERVAS'
                    WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%LENHOSA%' THEN 'PASTO COM LENHOSAS'
                    WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%INTERMEDIARIO%' OR UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%INTERMEDIÁRIO%' THEN 'INTERMEDIARIO'
                    WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%DEGRAD%' OR UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%DEG BIOLOGICA%' THEN 'DEG BIOLOGICA'
                    WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%REG%' OR UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%REGENERAÇÃO%' THEN 'REG NATURAL'
                    ELSE 'MISCELANEA'
                END AS tipologia_classe
            FROM '{EMBRAPA_PARQUET.as_posix()}'
        )
        SELECT 
            tipologia_classe,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / 701, 1) AS percentual
        FROM padronizado
        GROUP BY tipologia_classe
        ORDER BY total DESC
    """

    df_dist = con.execute(query_dist).df()

    distribution = {}
    for row in df_dist.itertuples(index=False):
        distribution[row.tipologia_classe] = {
            'total': int(row.total),
            'percentual': float(row.percentual)
        }

    # 2. Extract all 701 ground-truth points with coordinates and condition labels
    query_pts = f"""
        SELECT 
            TARGET_FID AS fid,
            ROUND(latitude, 5) AS lat,
            ROUND(longitude, 5) AS lon,
            CASE 
                WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%PRODUTIVO%' THEN 'PASTO PRODUTIVO'
                WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%ERVA%' THEN 'PASTO COM ERVAS'
                WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%LENHOSA%' THEN 'PASTO COM LENHOSAS'
                WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%INTERMEDIARIO%' OR UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%INTERMEDIÁRIO%' THEN 'INTERMEDIARIO'
                WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%DEGRAD%' OR UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%DEG BIOLOGICA%' THEN 'DEG BIOLOGICA'
                WHEN UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%REG%' OR UPPER(COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)) LIKE '%REGENERAÇÃO%' THEN 'REG NATURAL'
                ELSE 'MISCELANEA'
            END AS classe
        FROM '{EMBRAPA_PARQUET.as_posix()}'
        ORDER BY TARGET_FID
    """

    df_pts = con.execute(query_pts).df()
    points = []
    for row in df_pts.itertuples(index=False):
        points.append({
            'fid': int(row.fid) if row.fid is not None else -1,
            'lat': float(row.lat) if row.lat is not None else 0.0,
            'lon': float(row.lon) if row.lon is not None else 0.0,
            'classe': str(row.classe)
        })

    payload = {
        'total_amostras': len(points),
        'fonte': 'Embrapa Cerrado (701 field ground-truth reference points)',
        'distribuicao': distribution,
        'pontos': points
    }

    # 3. Export JSON for the interactive web map
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, separators=(',', ':'), ensure_ascii=False)

    # 4. Export CSV for static downloads and reproducible data pipelines
    csv_rows = []
    for p in points:
        csv_rows.append({
            'fid': p['fid'],
            'latitude': f"{p['lat']:.5f}",
            'longitude': f"{p['lon']:.5f}",
            'classe': p['classe'],
            'typology_label': TYPOLOGY_LABELS.get(p['classe'], p['classe'])
        })

    for out_path in [OUT_CSV_DOCS, OUT_CSV_BASE]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['fid', 'latitude', 'longitude', 'classe', 'typology_label']
            )
            writer.writeheader()
            writer.writerows(csv_rows)

    print(f"[OK] Successfully exported JSON: {OUT_JSON}")
    print(f"[OK] Successfully exported CSV (docs): {OUT_CSV_DOCS}")
    print(f"[OK] Successfully exported CSV (base): {OUT_CSV_BASE}")
    print(f"     Total Embrapa reference points: {len(points)}")
    print("     Class distribution:")
    for k, v in distribution.items():
        print(f"       - {k}: {v['total']} ({v['percentual']}%)")


if __name__ == '__main__':
    export_embrapa_reference()
