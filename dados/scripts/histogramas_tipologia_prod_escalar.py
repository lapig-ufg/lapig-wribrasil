"""
histogramas_tipologia_prod_escalar.py
=====================================
Generates histograms from prod_escalar_embrapa_mapbiomas_filtrado.parquet:

  1. Comparative bar chart: Existing vs. Represented Samples (>= THRESHOLD) per Tipologia_
  2. Complete dot product distribution (unfiltered) per Tipologia_

Usage:
    python histogramas_tipologia_prod_escalar.py               # default: threshold = 0.95
    python histogramas_tipologia_prod_escalar.py --limiar 0.75
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
parser = argparse.ArgumentParser(description="Typology histograms by dot product similarity.")
parser.add_argument("--limiar", type=float, default=0.95,
                    help="Minimum similarity threshold (default: 0.95)")
args = parser.parse_args()

LIMIAR = args.limiar
LIMIAR_INT = int(LIMIAR * 100)

# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------
DIR_BASE = Path(__file__).resolve().parent.parent
DIR_SAIDA = DIR_BASE / "saida"
DIR_SAIDA_LIMIAR = DIR_SAIDA / str(LIMIAR_INT)
DIR_SAIDA_LIMIAR.mkdir(parents=True, exist_ok=True)

PARQUET = DIR_SAIDA / "prod_escalar_embrapa_mapbiomas_filtrado.parquet"
COLUNA_ID = "TARGET_FID"
COLUNA_TIPOLOGIA = "Tipologia_"

CORES_Tipologia_ = {
    "PASTO PRODUTIVO": "#faea40",
    "PASTO COM ERVAS": "#d8ff6c",
    "REG NATURAL": "#0e5f0e",
    "INTERMEDIARIO": "#f4b346",
    "DEG BIOLOGICA": "#813209",
    "PASTO COM LENHOSAS": "#66c600",
    "MISCELANEA": "#ec2b10",
}


def estilo_limpo(ax):
    ax.set_facecolor("white")
    ax.figure.set_facecolor("white")
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.9, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(axis="both", length=0, labelsize=10, colors="#333333")


# ----------------------------------------------------------------
# Load Data
# ----------------------------------------------------------------
print(f"Loading data (threshold = {LIMIAR})...")
df = pd.read_parquet(PARQUET)
print(f"  {len(df):,} pairs loaded")

# Sort typologies by total sample count descending
amostras_total_raw = df.groupby(COLUNA_TIPOLOGIA)[COLUNA_ID].nunique()
ordem = amostras_total_raw.sort_values(ascending=False).index.tolist()
cores = {tip: CORES_Tipologia_.get(tip, "#cccccc") for tip in ordem}


# ================================================================
# CHART 1: Sample Comparison (Total vs. Match >= THRESHOLD)
# ================================================================
print(f"\nGenerating Histogram 1: sample comparison >= {LIMIAR}...")

# Filter pairs above threshold
df_filtrado = df[df["resultado_multiplicacao"] >= LIMIAR]

# Total unique samples per typology
amostras_total = df.groupby(COLUNA_TIPOLOGIA)[COLUNA_ID].nunique().reindex(ordem).fillna(0).astype(int)

# Unique samples with at least 1 match >= LIMIAR
amostras_filtradas = df_filtrado.groupby(COLUNA_TIPOLOGIA)[COLUNA_ID].nunique().reindex(ordem).fillna(0).astype(int)

# Represented percentage
pct_representada = (amostras_filtradas / amostras_total * 100).round(1)

# Grouped bar chart configuration
fig, ax = plt.subplots(figsize=(12, 7))
fig.subplots_adjust(top=0.82, bottom=0.22)

x = np.arange(len(ordem))
largura = 0.35

barras_total = ax.bar(x - largura/2, amostras_total.values, largura,
                      label="Total Samples", color="#d9d9d9", edgecolor="white", linewidth=0.5, zorder=3)
barras_filtradas = ax.bar(x + largura/2, amostras_filtradas.values, largura,
                          label=f"Samples with Match >= {LIMIAR}",
                          color=[cores[t] for t in ordem], edgecolor="white", linewidth=0.5, zorder=3)

for b, valor in zip(barras_total, amostras_total.values):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 3,
            f"{valor}", ha="center", va="bottom", fontsize=9, color="#666666", fontweight="bold")

for b, valor, pct in zip(barras_filtradas, amostras_filtradas.values, pct_representada.values):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 3,
            f"{valor}\n({pct:.0f}%)", ha="center", va="bottom", fontsize=9, color="#222222", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(ordem, rotation=30, ha="right", fontsize=10)
ax.set_ylabel("Number of Samples (TARGET_FID)", fontsize=11, color="#333333")
ax.set_xlabel("Pasture Typology", fontsize=11, color="#333333")
ax.set_ylim(0, max(amostras_total.max(), amostras_filtradas.max()) * 1.20)
ax.legend(frameon=False, fontsize=10, loc="upper right")

estilo_limpo(ax)
fig.text(0.06, 0.97, f"Sample Representativeness by Typology (Threshold >= {LIMIAR})",
         fontsize=15, fontweight="bold", color="#222222", ha="left", va="top")
fig.text(0.06, 0.925, f"Comparison between total training samples and samples with at least 1 match >= {LIMIAR}",
         fontsize=10.5, color="#666666", ha="left", va="top")

caminho1 = DIR_SAIDA_LIMIAR / "histograma_tipologia_amostras_comparacao.png"
fig.savefig(caminho1, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  [ok] {caminho1.name}")


# ================================================================
# CHART 2: Dot Product Distribution by Typology (Unfiltered)
# ================================================================
print(f"\nGenerating Histogram 2: dot product distribution per typology...")

fig, axes = plt.subplots(len(ordem), 1, figsize=(10, 2.2 * len(ordem)), sharex=True)
fig.subplots_adjust(top=0.92, bottom=0.08, hspace=0.35)

bins = np.linspace(0.4, 1.0, 60)

for ax, tip in zip(axes, ordem):
    sub = df[df[COLUNA_TIPOLOGIA] == tip]["resultado_multiplicacao"]
    cor = cores[tip]

    ax.hist(sub, bins=bins, color=cor, edgecolor="white", linewidth=0.4, zorder=3)
    ax.axvline(LIMIAR, color="#e74c3c", linestyle="--", linewidth=1.2, zorder=4,
               label=f"Threshold >= {LIMIAR}" if tip == ordem[0] else "")

    pct_acima = (sub >= LIMIAR).mean() * 100
    n_total = len(sub)
    n_acima = (sub >= LIMIAR).sum()

    ax.set_ylabel("Matches", fontsize=8.5, color="#333333")
    ax.text(0.02, 0.85, f"{tip}  (n = {n_total:,} | >= {LIMIAR}: {n_acima:,} = {pct_acima:.1f}%)",
            transform=ax.transAxes, fontsize=9.5, fontweight="bold", color="#222222", va="top")

    estilo_limpo(ax)

axes[-1].set_xlabel("Dot Product (Cosine Similarity)", fontsize=11, color="#333333")
axes[0].legend(frameon=False, fontsize=9, loc="upper right")

fig.text(0.06, 0.97, "Dot Product Distribution by Typology (Unfiltered)",
         fontsize=15, fontweight="bold", color="#222222", ha="left", va="top")
fig.text(0.06, 0.94, f"Dotted red line indicates cutoff threshold ({LIMIAR})",
         fontsize=10.5, color="#666666", ha="left", va="top")

caminho2 = DIR_SAIDA_LIMIAR / "histograma_tipologia_prod_escalar_distribuicao.png"
fig.savefig(caminho2, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  [ok] {caminho2.name}")

print(f"\nAll histograms generated and saved to: {DIR_SAIDA_LIMIAR}")
