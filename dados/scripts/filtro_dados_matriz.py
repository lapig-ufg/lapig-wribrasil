"""
filtro_dados_matriz.py
======================
Filters similarity matrix retaining only values >= THRESHOLD.
Values below the threshold are replaced with NaN.

Usage:
    python filtro_dados_matriz.py               # default: threshold = 0.95
    python filtro_dados_matriz.py --limiar 0.75
"""

import argparse
import pandas as pd
from pathlib import Path

# ----------------------------------------------------------------
# Command Line Arguments
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Filters similarity matrix by threshold.")
parser.add_argument("--limiar", type=float, default=0.95,
                    help="Minimum similarity threshold (default: 0.95)")
args = parser.parse_args()

LIMIAR = args.limiar
LIMIAR_INT = int(LIMIAR * 100)  # e.g., 95 or 75

# ----------------------------------------------------------------
# Project Paths
# ----------------------------------------------------------------
DIR_BASE = Path(__file__).resolve().parent.parent
DIR_SAIDA = DIR_BASE / "saida"
DIR_SAIDA_LIMIAR = DIR_SAIDA / str(LIMIAR_INT)
DIR_SAIDA_LIMIAR.mkdir(parents=True, exist_ok=True)

caminho_entrada = DIR_SAIDA / "matriz_similaridade_2024.parquet"
caminho_saida = DIR_SAIDA_LIMIAR / f"matriz_similaridade_2024_mais_{LIMIAR_INT}.csv"

# ----------------------------------------------------------------
# Processing
# ----------------------------------------------------------------
print(f"Filtering matrix with threshold >= {LIMIAR} ...")
print(f"  Input:  {caminho_entrada}")
print(f"  Output: {caminho_saida}")

# 1. Load Parquet file
df = pd.read_parquet(caminho_entrada)

# 2. Preserve identification and coordinate columns
colunas_protegidas = ['id_mapbiomas', 'latitude_alvo', 'longitude_alvo']
colunas_alvo = [col for col in df.columns if col not in colunas_protegidas]

# 3. Apply threshold condition (values < LIMIAR become NaN)
df[colunas_alvo] = df[colunas_alvo].where(df[colunas_alvo] >= LIMIAR)

# 4. Save output CSV
df.to_csv(caminho_saida, index=False)

print(f"File saved successfully: {caminho_saida.name}")
