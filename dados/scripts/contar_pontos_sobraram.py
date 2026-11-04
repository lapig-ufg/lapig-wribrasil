"""
contar_pontos_sobraram.py
=========================
Counts how many matches (non-null values) exist per MapBiomas pixel
in the filtered CSV, and generates a histogram with configurable bin steps (e.g., 5 or 50).

Usage:
    python contar_pontos_sobraram.py               # default: threshold = 0.95 (bin_step = 5)
    python contar_pontos_sobraram.py --limiar 0.75 # default: threshold = 0.75 (bin_step = 50)
    python contar_pontos_sobraram.py --limiar 0.75 --bin-step 50
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# ----------------------------------------------------------------
# Command Line Arguments
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Count matches per pixel in filtered CSV.")
parser.add_argument("--limiar", type=float, default=0.95,
                    help="Similarity threshold used in filtering (default: 0.95)")
parser.add_argument("--bin-step", type=int, default=None,
                    help="Histogram bin step size (e.g., 5 or 50)")
args = parser.parse_args()

LIMIAR = args.limiar
LIMIAR_INT = int(LIMIAR * 100)

# If bin-step is not specified, use 50 for thresholds <= 0.75 and 5 for larger thresholds
if args.bin_step is not None:
    STEP = args.bin_step
else:
    STEP = 50 if LIMIAR <= 0.75 else 5

# ----------------------------------------------------------------
# Project Paths
# ----------------------------------------------------------------
DIR_BASE = Path(__file__).resolve().parent.parent
DIR_SAIDA = DIR_BASE / "saida"
DIR_SAIDA_LIMIAR = DIR_SAIDA / str(LIMIAR_INT)
DIR_SAIDA_LIMIAR.mkdir(parents=True, exist_ok=True)

caminho_csv = DIR_SAIDA_LIMIAR / f"matriz_similaridade_2024_mais_{LIMIAR_INT}.csv"

# ----------------------------------------------------------------
# 1. Load Filtered CSV
# ----------------------------------------------------------------
print(f"Loading filtered CSV file (threshold >= {LIMIAR})...")
print(f"  File: {caminho_csv}")
df = pd.read_csv(caminho_csv)

# 2. Identify ID and coordinate columns
colunas_protegidas = ['id_mapbiomas', 'latitude_alvo', 'longitude_alvo']
colunas_pontos = [col for col in df.columns if col not in colunas_protegidas]

# 3. Count non-null matches per row
df['n_matches'] = df[colunas_pontos].notna().sum(axis=1)

# 4. Preview first rows
print("\nFirst rows preview with match count:")
print(df[['id_mapbiomas', 'latitude_alvo', 'longitude_alvo', 'n_matches']].head(10))

# 5. Statistical summary
print(f"\nStatistical summary of n_matches (>= {LIMIAR}) per MapBiomas point:")
print(df['n_matches'].describe())

# 6. Save summary CSV
caminho_resumo = DIR_SAIDA_LIMIAR / 'resumo_contagem_pontos_por_mapbiomas.csv'
df[['id_mapbiomas', 'latitude_alvo', 'longitude_alvo', 'n_matches']].to_csv(caminho_resumo, index=False)
print(f"\nSummary table saved to: {caminho_resumo.name}")

# ---------------------------------------------------------------------------
# 7. GENERATE HISTOGRAM (BINS STEP BY STEP)
# ---------------------------------------------------------------------------
print(f"\nGenerating histogram with intervals of {STEP}...")

max_matches = df['n_matches'].max()
bins = range(0, max_matches + STEP + 1, STEP)

fig, ax = plt.subplots(figsize=(12, 6))

ax.set_facecolor("white")
fig.set_facecolor("white")
ax.grid(axis="y", color="#e6e6e6", linewidth=0.9, zorder=0)
ax.set_axisbelow(True)
for spine in ["top", "right", "left"]:
    ax.spines[spine].set_visible(False)
ax.spines["bottom"].set_color("#cccccc")
ax.tick_params(axis="both", length=0, labelsize=10, colors="#333333")

n, bins_out, patches = ax.hist(
    df['n_matches'],
    bins=bins,
    color="#1abc9c",
    edgecolor="white",
    linewidth=1.2,
    zorder=3
)

for i, patch in enumerate(patches):
    if i == 0:
        patch.set_facecolor("#ff7f6b")  # Highlight initial bin
    else:
        patch.set_facecolor("#2ea6ff")

for i in range(len(n)):
    if n[i] > 0:
        ax.text(
            (bins[i] + bins[i+1]) / 2,
            n[i] + max(n) * 0.015,
            f"{int(n[i])}",
            ha="center",
            va="bottom",
            fontsize=8.5,
            color="#222222",
            fontweight="bold"
        )

n_pixels = len(df)
fig.text(0.06, 0.96, f"Distribution of n_matches per MapBiomas Point (Bin Step = {STEP})",
         fontsize=14, fontweight="bold", color="#222222", ha="left", va="top")
fig.text(0.06, 0.915, f"Total of {n_pixels:,} MapBiomas pixels | Similarity threshold >= {LIMIAR} | Bin size {STEP}",
         fontsize=10.5, color="#666666", ha="left", va="top")

ax.set_xlabel("Number of Matches per Pixel (n_matches)", fontsize=11, color="#333333")
ax.set_ylabel("MapBiomas Pixels Count", fontsize=11, color="#333333")
ax.set_xticks(range(0, max_matches + STEP + 1, STEP))
plt.xticks(rotation=45)

plt.tight_layout()
fig.subplots_adjust(top=0.85)

caminho_grafico = DIR_SAIDA_LIMIAR / f"histograma_n_matches_{STEP}em{STEP}.png"
plt.savefig(caminho_grafico, dpi=200, bbox_inches="tight")

caminho_legado = DIR_SAIDA_LIMIAR / "histograma_n_matches_5em5.png"
plt.savefig(caminho_legado, dpi=200, bbox_inches="tight")

plt.close(fig)

print(f"Histogram saved to: {caminho_grafico.name}")
print(f"Output folder: {DIR_SAIDA_LIMIAR}")
