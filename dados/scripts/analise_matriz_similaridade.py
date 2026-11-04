"""
analise_matriz_similaridade.py
==============================
Analyzes the pivoted Top-3 table (tabela_top3_pivotada.parquet) generated from
dot products between MapBiomas candidate points and Embrapa reference points.

For each MapBiomas point (id_alvo), contains the top 3 TARGET_FIDs with highest
dot product, class_embrapa (= top-1 typology), and the md3 agreement metric.

Generated figures (saved in saida/):
  1. Distribution of class_embrapa by Tipologia_ (sample count per class).
  2. Distribution of md3 metric (agreement across top-3 matches).
  3. Top 25 TARGET_FIDs that most frequently appear as best match (target_fid_1).
  4. Boxplots of ground cover composition (grass, woody, weed, bare soil) by class_embrapa.
  5. Elevation boxplot of top-1 by class_embrapa.

Usage:
    python analise_matriz_similaridade.py
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Analyzes pivoted Top-3 table.")
parser.add_argument("--limiar", type=float, default=None,
                    help="Similarity threshold for folder organization")
args, _ = parser.parse_known_args()

DIR_BASE = Path(__file__).resolve().parent.parent
DIR_SAIDA = DIR_BASE / "saida"
if args.limiar is not None:
    DIR_SAIDA = DIR_SAIDA / str(int(args.limiar * 100))
DIR_SAIDA.mkdir(parents=True, exist_ok=True)

PARQUET = DIR_BASE / "output" / "tabela_top3_pivotada.parquet"
if not PARQUET.exists():
    alt = DIR_BASE / "arquivos_saida" / "tabela_top3_pivotada_11k_2025.parquet"
    if alt.exists():
        PARQUET = alt

CORES_TIPOLOGIA = {
    "PASTO PRODUTIVO": "#faea40",
    "PASTO COM ERVAS": "#d8ff6c",
    "REG NATURAL": "#0e5f0e",
    "INTERMEDIARIO": "#f4b346",
    "DEG BIOLOGICA": "#813209",
    "PASTO COM LENHOSAS": "#66c600",
    "MISCELANEA": "#ec2b10",
}

VALORES_EXCLUIR = ["nao se aplica", "não se aplica", "NA", "nan"]


def estilo_limpo(ax):
    ax.set_facecolor("white")
    ax.figure.set_facecolor("white")
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.9, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(axis="both", length=0, labelsize=10, colors="#333333")


def titulo_subtitulo(fig, titulo, subtitulo):
    fig.text(0.06, 0.97, titulo, fontsize=15, fontweight="bold",
             color="#222222", ha="left", va="top")
    fig.text(0.06, 0.925, subtitulo, fontsize=10.5, color="#666666",
             ha="left", va="top")


# ----------------------------------------------------------------
# 1. Load Data
# ----------------------------------------------------------------
print("=" * 70)
print("ANALYSIS OF PIVOTED TOP-3 TABLE (11K)")
print("=" * 70)
print(f"\n[1/6] Loading {PARQUET.name}...")

if not PARQUET.exists():
    print(f"File not found: {PARQUET}. Skipping.")
    exit(0)

df = pd.read_parquet(PARQUET)

df = df[~df["class_embrapa"].isin(VALORES_EXCLUIR)].copy()
print(f"  {len(df):,} MapBiomas points loaded")

contagem_classes = df["class_embrapa"].value_counts()
ordem = contagem_classes.index.tolist()
cores = {tip: CORES_TIPOLOGIA.get(tip, "#cccccc") for tip in ordem}


# ----------------------------------------------------------------
# 2a. Chart 1: MapBiomas points by class_embrapa (Simple)
# ----------------------------------------------------------------
print("\n[2a/6] Generating Chart 1: MapBiomas points by class_embrapa...")

fig, ax = plt.subplots(figsize=(11, 7))
fig.subplots_adjust(top=0.82, bottom=0.22)

barras = ax.bar(range(len(ordem)), contagem_classes.values,
                color=[cores[t] for t in ordem],
                width=0.65, zorder=3, edgecolor="white", linewidth=0.5)

for barra, valor in zip(barras, contagem_classes.values):
    pct = valor / len(df) * 100
    ax.text(barra.get_x() + barra.get_width() / 2,
            barra.get_height() + contagem_classes.max() * 0.015,
            f"{valor:,}\n({pct:.1f}%)",
            ha="center", va="bottom", fontsize=9.5,
            color="#222222", fontweight="bold")

ax.set_xticks(range(len(ordem)))
ax.set_xticklabels(ordem, rotation=30, ha="right", fontsize=10)
ax.set_ylabel("MapBiomas Points Count", fontsize=11, color="#333333")
ax.set_xlabel("Embrapa Reference Class (Top-1 Typology)", fontsize=11, color="#333333")
ax.set_ylim(0, contagem_classes.max() * 1.20)

estilo_limpo(ax)
titulo_subtitulo(fig,
    "Classification of MapBiomas Points via Similarity (Top-1)",
    f"{len(df):,} points classified by highest dot-product TARGET_FID")

caminho1 = DIR_SAIDA / "pontos_por_class_embrapa.png"
fig.savefig(caminho1, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  [ok] {caminho1.name}")


# ----------------------------------------------------------------
# 3. Chart 2: Md3 Agreement Distribution
# ----------------------------------------------------------------
print("\n[3/6] Generating Chart 2: md3 distribution...")

md3_counts = df["md3"].value_counts().sort_index()
md3_labels = {
    1: "md3 = 1\n(no agreement)",
    2: "md3 = 2\n(1 of 2 agree)",
    3: "md3 = 3\n(all 3 agree)"
}
md3_cores = ["#ff7f6b", "#c9a300", "#1abc9c"]

fig, ax = plt.subplots(figsize=(9, 6))
fig.subplots_adjust(top=0.82, bottom=0.18)

labels = [md3_labels.get(v, str(v)) for v in md3_counts.index]
barras = ax.bar(range(len(md3_counts)), md3_counts.values,
                color=md3_cores[:len(md3_counts)],
                width=0.55, zorder=3, edgecolor="white", linewidth=0.5)

for barra, valor in zip(barras, md3_counts.values):
    pct = valor / len(df) * 100
    ax.text(barra.get_x() + barra.get_width() / 2,
            barra.get_height() + md3_counts.max() * 0.02,
            f"{valor:,}\n({pct:.1f}%)",
            ha="center", va="bottom", fontsize=10.5,
            color="#222222", fontweight="bold")

ax.set_xticks(range(len(md3_counts)))
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("MapBiomas Points Count", fontsize=11, color="#333333")
ax.set_ylim(0, md3_counts.max() * 1.22)

estilo_limpo(ax)
titulo_subtitulo(fig,
    "Agreement Across Top-3 Matches (md3)",
    "Count of top-3 matching reference points that assign the identical class")

caminho2 = DIR_SAIDA / "distribuicao_md3.png"
fig.savefig(caminho2, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  [ok] {caminho2.name}")


# ----------------------------------------------------------------
# 4. Chart 3: Top 25 TARGET_FIDs as Top-1
# ----------------------------------------------------------------
print("\n[4/6] Generating Chart 3: top 25 TARGET_FIDs...")

top_targets = df["target_fid_1"].value_counts().head(25)
df_top = top_targets.iloc[::-1]

fid_to_class = df.drop_duplicates("target_fid_1").set_index("target_fid_1")["tipologia_1"]
classes_top = [fid_to_class.get(fid, "?") for fid in df_top.index]
cores_bar = [cores.get(c, "#cccccc") for c in classes_top]

fig, ax = plt.subplots(figsize=(12, 9))
fig.subplots_adjust(top=0.88, left=0.15, right=0.82)

barras = ax.barh(range(len(df_top)), df_top.values,
                 color=cores_bar, height=0.7, zorder=3,
                 edgecolor="white", linewidth=0.5)

for barra, valor in zip(barras, df_top.values):
    pct = valor / len(df) * 100
    ax.text(barra.get_width() + df_top.max() * 0.01,
            barra.get_y() + barra.get_height() / 2,
            f"{valor:,} ({pct:.1f}%)",
            ha="left", va="center", fontsize=9, color="#333333")

ax.set_yticks(range(len(df_top)))
ax.set_yticklabels([f"FID {int(fid)}" for fid in df_top.index], fontsize=9.5)
ax.set_xlabel("Classified MapBiomas Points Count", fontsize=11, color="#333333")
ax.set_xlim(0, df_top.max() * 1.25)

estilo_limpo(ax)
ax.grid(axis="y", visible=False)
ax.grid(axis="x", color="#e6e6e6", linewidth=0.9, zorder=0)

from matplotlib.patches import Patch
classes_presentes = list(dict.fromkeys(classes_top))
legend_handles = [Patch(facecolor=cores.get(c, "#ccc"), edgecolor="#555",
                        label=c) for c in sorted(classes_presentes)]
ax.legend(handles=legend_handles, title="Class (Tipologia_)",
          fontsize=9, title_fontsize=10, loc="lower right",
          framealpha=0.9, edgecolor="#cccccc")

titulo_subtitulo(fig,
    "Top 25 Most Representative Embrapa Samples (Top-1)",
    "TARGET_FIDs that most frequently serve as top-1 match for MapBiomas points")

caminho3 = DIR_SAIDA / "top25_target_fids.png"
fig.savefig(caminho3, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  [ok] {caminho3.name}")


# ----------------------------------------------------------------
# 5. Chart 4: Ground Cover Composition by Class
# ----------------------------------------------------------------
print("\n[5/6] Generating Chart 4: ground cover composition...")

variaveis = ["capim_1", "lenhosa_co_1", "ruderal_1", "solo_1"]
var_labels = ["Grass (Capim)", "Woody (Lenhosa)", "Weeds (Ruderal)", "Bare Soil (Solo)"]

fig, axes = plt.subplots(2, 2, figsize=(13, 9))
fig.subplots_adjust(top=0.88, hspace=0.55, wspace=0.25, bottom=0.12)

for ax, var, var_label in zip(axes.flat, variaveis, var_labels):
    dados = [df.loc[df["class_embrapa"] == cat, var].dropna().values for cat in ordem]
    bp = ax.boxplot(dados, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#333333", linewidth=1.5))
    for patch, cat in zip(bp["boxes"], ordem):
        patch.set_facecolor(cores[cat])
        patch.set_alpha(0.75)
        patch.set_edgecolor("#555555")
    ax.set_xticks(range(1, len(ordem) + 1))
    ax.set_xticklabels(ordem, rotation=35, ha="right", fontsize=8.5)
    ax.set_title(var_label, fontsize=11, fontweight="bold", color="#333333")
    estilo_limpo(ax)

titulo_subtitulo(fig,
    "Ground Cover Composition of Top-1 Match by Class",
    "Percentage distribution of grass, woody cover, weeds, and bare soil in top-1 match")

caminho4 = DIR_SAIDA / "composicao_por_class_embrapa.png"
fig.savefig(caminho4, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  [ok] {caminho4.name}")


# ----------------------------------------------------------------
# 6. Chart 5: Elevation by Class
# ----------------------------------------------------------------
print("\n[6/6] Generating Chart 5: elevation by class_embrapa...")

dados = [df.loc[df["class_embrapa"] == cat, "altitude_1"].dropna().values for cat in ordem]

fig, ax = plt.subplots(figsize=(9, 6))
fig.subplots_adjust(top=0.85, bottom=0.28)

bp = ax.boxplot(dados, patch_artist=True, showfliers=False,
                medianprops=dict(color="#333333", linewidth=1.5))
for patch, cat in zip(bp["boxes"], ordem):
    patch.set_facecolor(cores[cat])
    patch.set_alpha(0.75)
    patch.set_edgecolor("#555555")

ax.set_xticks(range(1, len(ordem) + 1))
ax.set_xticklabels(ordem, rotation=30, ha="right")
ax.set_ylabel("Elevation (m)", fontsize=11, color="#333333")

estilo_limpo(ax)
titulo_subtitulo(fig,
    "Elevation of Top-1 Match by Class",
    "Elevation (meters) distribution of top-1 TARGET_FID for each class_embrapa")

caminho5 = DIR_SAIDA / "altitude_por_class_embrapa.png"
fig.savefig(caminho5, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  [ok] {caminho5.name}")

print(f"\nAnalysis completed. Files saved to: {DIR_SAIDA}")
