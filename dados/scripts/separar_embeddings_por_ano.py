"""
separar_embeddings_por_ano.py
==============================
Splits multi-year file embeddings_50k_localizado_via_join.parquet
(containing lat_alvo and lon_alvo fields) into individual annual files (2019 to 2025)
of 50,000 sample points each.

Outputs: produto_escalar_metricas/arquivos_base/embeddings_samples_50k_cvp_s2_cerrado_{year}.parquet (~26 MB each)

Usage:
    python separar_embeddings_por_ano.py
"""

import duckdb
import time
from pathlib import Path

DIR_ROOT = Path(__file__).resolve().parent.parent
DIR_METRICAS = DIR_ROOT / "produto_escalar_metricas"
DIR_ARQUIVOS_BASE = DIR_METRICAS / "arquivos_base"
DIR_ARQUIVOS_BASE.mkdir(parents=True, exist_ok=True)

# Candidate multi-year files with priority given to files containing lat_alvo/lon_alvo
CANDIDATOS_MULTI_ANO = [
    DIR_ARQUIVOS_BASE / "embeddings_50k_localizado_via_join.parquet",
    DIR_ROOT / "data" / "embeddings_50k_localizado_via_join.parquet",
    DIR_ARQUIVOS_BASE / "embeddings_samples_50k_cvp_s2_cerrado_2019_2025_v1.parquet"
]


def obter_parquet_multi_ano():
    for p in CANDIDATOS_MULTI_ANO:
        if p.exists():
            return p
    return None


def separar_anos():
    print("=" * 70)
    print("SPLITTING 50K EMBEDDINGS BY YEAR (WITH LAT_ALVO AND LON_ALVO)")
    print("=" * 70)

    parquet_multi_ano = obter_parquet_multi_ano()
    if not parquet_multi_ano:
        print("Error: No multi-year base file found in:")
        for p in CANDIDATOS_MULTI_ANO:
            print(f"  - {p}")
        return

    con = duckdb.connect()

    # Identify available years
    anos_rows = con.execute(f"""
        SELECT DISTINCT year, count(*) 
        FROM '{parquet_multi_ano.as_posix()}' 
        GROUP BY year 
        ORDER BY year
    """).fetchall()

    print(f"\nSource multi-year file: {parquet_multi_ano.name}")
    print("Identified years:")
    for ano, cnt in anos_rows:
        print(f"  - {ano}: {cnt:,} points")

    t_total = time.time()
    for ano, cnt in anos_rows:
        out_file = DIR_ARQUIVOS_BASE / f"embeddings_samples_50k_cvp_s2_cerrado_{ano}.parquet"
        t0 = time.time()
        print(f"\nExporting {ano} ({cnt:,} records) -> {out_file.name} ...")

        con.execute(f"""
            COPY (
                SELECT * 
                FROM '{parquet_multi_ano.as_posix()}' 
                WHERE year = {ano}
                ORDER BY id
            ) TO '{out_file.as_posix()}' (FORMAT PARQUET)
        """)

        size_mb = out_file.stat().st_size / (1024 * 1024)
        print(f"  Completed in {time.time() - t0:.2f}s ({size_mb:.2f} MB)")

    print("\n" + "=" * 70)
    print(f"All {len(anos_rows)} years split successfully in {time.time() - t_total:.2f}s!")
    print("=" * 70)


if __name__ == "__main__":
    separar_anos()
