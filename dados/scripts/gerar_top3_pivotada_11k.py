"""
gerar_top3_pivotada_11k.py
==========================
Processing pipeline for Dot Product and pivoted Top-3 similarity tables
for the 11k/12k sample base (MapBiomas Pasture Col11 + MapBiomas 85k) crossed
with the 701 Embrapa field reference points across the entire historical series (2019–2025).

Corrections and Standardizations Applied:
1. Coordinate Inversion Correction in embeddings_avg_mapbiomas_pastagem_2019_2025:
   - lat_alvo = lon (-24 to -2)
   - lon_alvo = lat (-60 to -41)
2. Coordinates in embeddings_avg_mapbiomas85k_2019_2025:
   - lat_alvo = LAT
   - lon_alvo = LON
3. Standardization of pasture classes:
   - Pasture and Natural Pasture (Col11) + PASTAGEM (85k)
4. 64-dimensional dot product calculation (A00 to A63) and Md3 agreement index.

Usage:
    python gerar_top3_pivotada_11k.py --year 2025
    python gerar_top3_pivotada_11k.py --year all
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
import duckdb

# Base directories
DIR_SCRIPT = Path(__file__).resolve().parent
DIR_DADOS = DIR_SCRIPT.parent
DIR_ROOT = DIR_DADOS.parent

DIR_BASE = DIR_DADOS / "arquivos_base"
DIR_SAIDA = DIR_DADOS / "arquivos_saida"
DIR_ASSETS = DIR_ROOT / "docs" / "assets"

ARQ_85K = DIR_BASE / "embeddings_avg_mapbiomas85k_2019_2025.parquet"
ARQ_PASTAGEM = DIR_BASE / "embeddings_avg_mapbiomas_pastagem_2019_2025.parquet"
ARQ_EMBRAPA = DIR_BASE / "embeddings_embrapa_year_colet.parquet"

# Official typology mapping
TIP_MAP = {
    'PASTO PRODUTIVO': 0, 'PRODUTIVO': 0,
    'PASTO COM ERVAS': 1,
    'PASTO COM LENHOSAS': 2,
    'INTERMEDIARIO': 3, 'INTERMEDIÁRIO': 3,
    'DEG BIOLOGICA': 4, 'DEG BIOLÓGICA': 4,
    'REG NATURAL': 5,
    'MISCELANEA': 6, 'MISCELÂNEA': 6,
    'Outros': 7
}

TIP_LIST = [
    'PASTO PRODUTIVO', 'PASTO COM ERVAS', 'PASTO COM LENHOSAS',
    'INTERMEDIARIO', 'DEG BIOLOGICA', 'REG NATURAL', 'MISCELANEA', 'Outros'
]


def padronizar_tipologia_sql(col_raw):
    return f"""
        CASE 
            WHEN UPPER({col_raw}) LIKE '%PRODUTIVO%' THEN 'PASTO PRODUTIVO'
            WHEN UPPER({col_raw}) LIKE '%ERVA%' THEN 'PASTO COM ERVAS'
            WHEN UPPER({col_raw}) LIKE '%LENHOSA%' THEN 'PASTO COM LENHOSAS'
            WHEN UPPER({col_raw}) LIKE '%INTERMEDIARIO%' OR UPPER({col_raw}) LIKE '%INTERMEDIÁRIO%' THEN 'INTERMEDIARIO'
            WHEN UPPER({col_raw}) LIKE '%DEGRAD%' OR UPPER({col_raw}) LIKE '%DEG BIOLOGICA%' OR UPPER({col_raw}) LIKE '%DEG BIOLÓGICA%' THEN 'DEG BIOLOGICA'
            WHEN UPPER({col_raw}) LIKE '%REG%' OR UPPER({col_raw}) LIKE '%REGENERAÇÃO%' OR UPPER({col_raw}) LIKE '%REGENERACAO%' THEN 'REG NATURAL'
            ELSE 'MISCELANEA'
        END
    """


def processar_ano(ano: int, con: duckdb.DuckDBPyConnection):
    t0 = time.time()
    print(f"\n{'-' * 65}")
    print(f"Processing 11k Top-3 Series for year: {ano}")

    col_85k_class = f"CLASS_{min(ano, 2024)}"
    col_past_class = f"class_{ano}"

    # Output files (saves with both 11k and 12k prefixes for backwards compatibility)
    out_parquet = DIR_SAIDA / f"tabela_top3_pivotada_11k_{ano}.parquet"
    out_parquet_12k = DIR_SAIDA / f"tabela_top3_pivotada_12k_{ano}.parquet"
    out_csv = DIR_SAIDA / f"tabela_top3_11k_{ano}.csv"
    out_csv_assets = DIR_ASSETS / f"tabela_top3_11k_{ano}.csv"
    out_csv_assets_12k = DIR_ASSETS / f"tabela_top3_12k_{ano}.csv"
    out_json_assets = DIR_ASSETS / f"tabela_top3_11k_{ano}.json"
    out_json_assets_12k = DIR_ASSETS / f"tabela_top3_12k_{ano}.json"

    # Dot product terms (A00*A00 + ... + A63*A63)
    prod_terms = " + ".join([f"(e.A{i:02d} * m.A{i:02d})" for i in range(64)])

    tip_embrapa_expr = padronizar_tipologia_sql("COALESCE(NULLIF(TIPOLOGIAc, 'nao se aplica'), Tipologia_)")

    sql_query = f"""
        -- 1. Filtered and Unified MapBiomas Base for year {ano}
        WITH mapbiomas_pastagem AS (
            SELECT 
                CAST(id AS VARCHAR) AS id_origem,
                'mapbiomas_pastagem_col11' AS fonte,
                {col_past_class} AS class_mapbiomas,
                -- Documented coordinate inversion fix:
                lon AS lat_alvo,
                lat AS lon_alvo,
                A00, A01, A02, A03, A04, A05, A06, A07, A08, A09,
                A10, A11, A12, A13, A14, A15, A16, A17, A18, A19,
                A20, A21, A22, A23, A24, A25, A26, A27, A28, A29,
                A30, A31, A32, A33, A34, A35, A36, A37, A38, A39,
                A40, A41, A42, A43, A44, A45, A46, A47, A48, A49,
                A50, A51, A52, A53, A54, A55, A56, A57, A58, A59,
                A60, A61, A62, A63
            FROM '{ARQ_PASTAGEM.as_posix()}'
            WHERE year = {ano} 
              AND {col_past_class} = 'Pastagem'
        ),
        mapbiomas_85k AS (
            SELECT 
                CAST(ID_REVISAO AS VARCHAR) AS id_origem,
                'mapbiomas_85k_col5' AS fonte,
                {col_85k_class} AS class_mapbiomas,
                -- Coordinates already aligned:
                LAT AS lat_alvo,
                LON AS lon_alvo,
                A00, A01, A02, A03, A04, A05, A06, A07, A08, A09,
                A10, A11, A12, A13, A14, A15, A16, A17, A18, A19,
                A20, A21, A22, A23, A24, A25, A26, A27, A28, A29,
                A30, A31, A32, A33, A34, A35, A36, A37, A38, A39,
                A40, A41, A42, A43, A44, A45, A46, A47, A48, A49,
                A50, A51, A52, A53, A54, A55, A56, A57, A58, A59,
                A60, A61, A62, A63
            FROM '{ARQ_85K.as_posix()}'
            WHERE year = {ano} 
              AND UPPER({col_85k_class}) = 'PASTAGEM'
        ),
        mapbiomas_unificado AS (
            SELECT 
                ROW_NUMBER() OVER () AS id_alvo,
                * 
            FROM (
                SELECT * FROM mapbiomas_pastagem
                UNION ALL
                SELECT * FROM mapbiomas_85k
            )
        ),
        -- 2. Standardized Embrapa Base (701 field ground-truth points)
        embrapa_ref AS (
            SELECT 
                TARGET_FID AS target_fid,
                Tipologia_ AS tipologia_raw,
                {tip_embrapa_expr} AS tipologia_classe,
                altitude,
                capim,
                lenhosa_co,
                ruderal,
                solo,
                latitude AS lat_ref,
                longitude AS lon_ref,
                year_colet,
                A00, A01, A02, A03, A04, A05, A06, A07, A08, A09,
                A10, A11, A12, A13, A14, A15, A16, A17, A18, A19,
                A20, A21, A22, A23, A24, A25, A26, A27, A28, A29,
                A30, A31, A32, A33, A34, A35, A36, A37, A38, A39,
                A40, A41, A42, A43, A44, A45, A46, A47, A48, A49,
                A50, A51, A52, A53, A54, A55, A56, A57, A58, A59,
                A60, A61, A62, A63
            FROM '{ARQ_EMBRAPA.as_posix()}'
        ),
        -- 3. Dot Product and Top-3 Ranking
        ranked_matches AS (
            SELECT 
                m.id_alvo,
                m.id_origem,
                m.fonte,
                m.class_mapbiomas,
                m.lat_alvo,
                m.lon_alvo,
                e.target_fid,
                e.tipologia_classe,
                e.tipologia_raw,
                e.altitude,
                e.capim,
                e.lenhosa_co,
                e.ruderal,
                e.solo,
                e.year_colet,
                CAST(ROUND(e.lat_ref, 4) AS VARCHAR) || ', ' || CAST(ROUND(e.lon_ref, 4) AS VARCHAR) AS loc_ref,
                ({prod_terms}) AS prod_escalar,
                ROW_NUMBER() OVER (
                    PARTITION BY m.id_alvo 
                    ORDER BY ({prod_terms}) DESC
                ) AS rn
            FROM mapbiomas_unificado m
            CROSS JOIN embrapa_ref e
            QUALIFY rn <= 3
        ),
        -- 4. Pivoting Top-3 Attributes
        pivoted AS (
            SELECT 
                id_alvo,
                MAX(CASE WHEN rn = 1 THEN id_origem END) AS id_origem,
                MAX(CASE WHEN rn = 1 THEN fonte END) AS fonte,
                MAX(CASE WHEN rn = 1 THEN class_mapbiomas END) AS class_mapbiomas,
                MAX(CASE WHEN rn = 1 THEN lat_alvo END) AS lat_alvo,
                MAX(CASE WHEN rn = 1 THEN lon_alvo END) AS lon_alvo,

                -- Top 1
                MAX(CASE WHEN rn = 1 THEN target_fid END) AS target_fid_1,
                MAX(CASE WHEN rn = 1 THEN prod_escalar END) AS prod_escalar_1,
                MAX(CASE WHEN rn = 1 THEN tipologia_classe END) AS tipologia_c_1,
                MAX(CASE WHEN rn = 1 THEN tipologia_raw END) AS tipologia_1,
                MAX(CASE WHEN rn = 1 THEN loc_ref END) AS loc_1,
                MAX(CASE WHEN rn = 1 THEN altitude END) AS altitude_1,
                MAX(CASE WHEN rn = 1 THEN capim END) AS capim_1,
                MAX(CASE WHEN rn = 1 THEN lenhosa_co END) AS lenhosa_co_1,
                MAX(CASE WHEN rn = 1 THEN ruderal END) AS ruderal_1,
                MAX(CASE WHEN rn = 1 THEN solo END) AS solo_1,
                MAX(CASE WHEN rn = 1 THEN year_colet END) AS year_colet_1,

                -- Top 2
                MAX(CASE WHEN rn = 2 THEN target_fid END) AS target_fid_2,
                MAX(CASE WHEN rn = 2 THEN prod_escalar END) AS prod_escalar_2,
                MAX(CASE WHEN rn = 2 THEN tipologia_classe END) AS tipologia_c_2,
                MAX(CASE WHEN rn = 2 THEN tipologia_raw END) AS tipologia_2,
                MAX(CASE WHEN rn = 2 THEN loc_ref END) AS loc_2,

                -- Top 3
                MAX(CASE WHEN rn = 3 THEN target_fid END) AS target_fid_3,
                MAX(CASE WHEN rn = 3 THEN prod_escalar END) AS prod_escalar_3,
                MAX(CASE WHEN rn = 3 THEN tipologia_classe END) AS tipologia_c_3,
                MAX(CASE WHEN rn = 3 THEN tipologia_raw END) AS tipologia_3,
                MAX(CASE WHEN rn = 3 THEN loc_ref END) AS loc_3
            FROM ranked_matches
            GROUP BY id_alvo
        )
        SELECT 
            *,
            tipologia_c_1 AS class_embrapa,
            ROUND((prod_escalar_1 + prod_escalar_2 + prod_escalar_3) / 3.0, 4) AS md3,
            -- Categorical class agreement score:
            (1 + CASE WHEN tipologia_c_2 = tipologia_c_1 THEN 1 ELSE 0 END + CASE WHEN tipologia_c_3 = tipologia_c_1 THEN 1 ELSE 0 END) AS score_concordancia
        FROM pivoted
        ORDER BY id_alvo
    """

    # 1. Export Parquet
    con.execute(f"COPY ({sql_query}) TO '{out_parquet.as_posix()}' (FORMAT 'parquet', COMPRESSION 'zstd');")
    con.execute(f"COPY ({sql_query}) TO '{out_parquet_12k.as_posix()}' (FORMAT 'parquet', COMPRESSION 'zstd');")
    size_parquet = out_parquet.stat().st_size / (1024 * 1024)

    # 2. Export CSV
    con.execute(f"COPY (SELECT * FROM '{out_parquet.as_posix()}') TO '{out_csv.as_posix()}' (FORMAT 'csv', HEADER true);")
    con.execute(f"COPY (SELECT * FROM '{out_parquet.as_posix()}') TO '{out_csv_assets.as_posix()}' (FORMAT 'csv', HEADER true);")
    con.execute(f"COPY (SELECT * FROM '{out_parquet.as_posix()}') TO '{out_csv_assets_12k.as_posix()}' (FORMAT 'csv', HEADER true);")
    size_csv = out_csv_assets.stat().st_size / (1024 * 1024)

    # 3. Export Compact JSON for Web
    web_df = con.execute(f"""
        SELECT 
            id_alvo AS id,
            ROUND(lat_alvo, 4) AS lat,
            ROUND(lon_alvo, 4) AS lon,
            tipologia_c_1 AS tip1,
            ROUND(prod_escalar_1, 3) AS p1,
            target_fid_1 AS fid1,
            ROUND(md3, 3) AS md3,
            loc_1,
            1 AS cvp,
            target_fid_2 AS fid2,
            ROUND(prod_escalar_2, 3) AS p2,
            tipologia_c_2 AS tip2,
            loc_2,
            target_fid_3 AS fid3,
            ROUND(prod_escalar_3, 3) AS p3,
            tipologia_c_3 AS tip3,
            loc_3
        FROM '{out_parquet.as_posix()}'
    """).df()

    rows = []
    for row in web_df.itertuples(index=False):
        t1 = TIP_MAP.get(str(row.tip1).strip().upper() if row.tip1 else 'Outros', 7)
        t2 = TIP_MAP.get(str(row.tip2).strip().upper() if row.tip2 else 'Outros', 7)
        t3 = TIP_MAP.get(str(row.tip3).strip().upper() if row.tip3 else 'Outros', 7)
        rows.append([
            int(row.id),
            float(row.lat) if row.lat is not None else 0.0,
            float(row.lon) if row.lon is not None else 0.0,
            t1,
            float(row.p1) if row.p1 is not None else 0.0,
            int(row.fid1) if row.fid1 is not None else -1,
            float(row.md3) if row.md3 is not None else 0.0,
            str(row.loc_1) if row.loc_1 is not None else '',
            int(row.cvp) if row.cvp is not None else 1,
            int(row.fid2) if row.fid2 is not None else -1,
            float(row.p2) if row.p2 is not None else 0.0,
            t2,
            str(row.loc_2) if row.loc_2 is not None else '',
            int(row.fid3) if row.fid3 is not None else -1,
            float(row.p3) if row.p3 is not None else 0.0,
            t3,
            str(row.loc_3) if row.loc_3 is not None else ''
        ])

    compact_payload = {
        'dataset': '12k',
        'year': int(ano),
        'total': len(rows),
        'tipologias': TIP_LIST,
        'cols': ['id', 'lat', 'lon', 't1', 'p1', 'fid1', 'md3', 'loc1', 'cvp', 'fid2', 'p2', 't2', 'loc2', 'fid3', 'p3', 't3', 'loc3'],
        'data': rows
    }

    with open(out_json_assets, 'w', encoding='utf-8') as f:
        json.dump(compact_payload, f, separators=(',', ':'))

    with open(out_json_assets_12k, 'w', encoding='utf-8') as f:
        json.dump(compact_payload, f, separators=(',', ':'))

    size_json = out_json_assets.stat().st_size / (1024 * 1024)
    elapsed = time.time() - t0

    print(f"  [OK] Year {ano} completed in {elapsed:.2f}s:")
    print(f"       - Total Samples: {len(rows):,}")
    print(f"       - Parquet:       {size_parquet:.2f} MB")
    print(f"       - CSV:           {size_csv:.2f} MB")
    print(f"       - JSON:          {size_json:.2f} MB (Compact Web)")


def main():
    parser = argparse.ArgumentParser(description="Pivoted Top-3 Generator for 11k Series")
    parser.add_argument("--year", type=str, default="2025", help="Year to process (2019..2025 or 'all')")
    args = parser.parse_args()

    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    DIR_ASSETS.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    t_start = time.time()
    if args.year.lower() == "all":
        anos = list(range(2019, 2026))
    else:
        anos = [int(args.year)]

    print("=" * 65)
    print("PIVOTED TOP-3 TABLE GENERATOR — 11k SERIES (MAPBIOMAS)")
    print(f"Years to process: {anos}")
    print("=" * 65)

    for ano in anos:
        processar_ano(ano, con)

    t_total = time.time() - t_start
    print("\n" + "=" * 65)
    print(f"Processing completed successfully in {t_total:.2f}s!")
    print("=" * 65)


if __name__ == "__main__":
    main()
