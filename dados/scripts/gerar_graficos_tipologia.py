"""
gerar_graficos_tipologia.py
=============================
Generates exploratory data analysis charts from
`prod_escalar_embrapa_mapbiomas_filtrado.parquet` in relation to `Tipologia_`.

Generated charts (saved in saida/):
  1. Training samples by condition class (unique TARGET_FID count)
  2. Ground cover fraction boxplots (grass, woody, weed, bare soil) by typology
  3. Terrain elevation boxplot by typology

Usage:
    python gerar_graficos_tipologia.py

Requirements: pandas, matplotlib, pyarrow
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
DIR_BASE = Path(__file__).resolve().parent.parent
DIR_SAIDA = DIR_BASE / "saida"
CAMINHO_PARQUET = DIR_SAIDA / "prod_escalar_embrapa_mapbiomas_filtrado.parquet"
COLUNA_TIPOLOGIA = "Tipologia_"
COLUNA_ID = "TARGET_FID"
PASTA_SAIDA = DIR_SAIDA

CORES_Tipologia_ = {
    "PASTO PRODUTIVO": "#faea40",
    "PASTO COM ERVAS": "#d8ff6c",
    "REG NATURAL": "#0e5f0e",
    "INTERMEDIARIO": "#f4b346",
    "DEG BIOLOGICA": "#813209",
    "PASTO COM LENHOSAS": "#66c600",
    "MISCELANEA": "#ec2b10",
}

VALORES_EXCLUIR = ["nao se aplica", "não se aplica", "NA", "nan"]


# ---------------------------------------------------------------------------
# STYLING
# ---------------------------------------------------------------------------
def aplicar_estilo(ax):
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


# ---------------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------------
def carregar_dados(caminho=CAMINHO_PARQUET):
    df = pd.read_parquet(caminho)
    df = df[~df[COLUNA_TIPOLOGIA].isin(VALORES_EXCLUIR)].copy()
    return df


# ---------------------------------------------------------------------------
# CHART 1 — Training samples by condition class (Unique IDs)
# ---------------------------------------------------------------------------
def grafico_amostras_por_classe(df, salvar_como="amostras_por_tipologia.png"):
    contagem = (
        df.groupby(COLUNA_TIPOLOGIA)[COLUNA_ID]
        .nunique()
        .sort_values(ascending=False)
    )

    cores = [CORES_Tipologia_.get(cat, "#cccccc") for cat in contagem.index]

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.subplots_adjust(top=0.82, bottom=0.28)

    barras = ax.bar(contagem.index, contagem.values, color=cores,
                    width=0.65, zorder=3)

    for barra, valor in zip(barras, contagem.values):
        ax.text(barra.get_x() + barra.get_width() / 2,
                barra.get_height() + contagem.max() * 0.015,
                f"{valor}", ha="center", va="bottom",
                fontsize=10.5, color="#222222", fontweight="bold")

    ax.set_ylabel("Number of Samples", fontsize=11, color="#333333")
    ax.set_xlabel("Pasture Typology", fontsize=11, color="#333333")
    ax.set_ylim(0, contagem.max() * 1.12)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    aplicar_estilo(ax)
    titulo_subtitulo(fig, "Training Ground-Truth Samples by Class (Unique IDs)",
                     "Evaluates class balance across field reference points")

    fig.savefig(PASTA_SAIDA / salvar_como, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] {salvar_como}  ->  {contagem.to_dict()}")
    return contagem


# ---------------------------------------------------------------------------
# CHART 2 — Ground cover composition by typology (boxplots)
# ---------------------------------------------------------------------------
def grafico_composicao_por_tipologia(df, salvar_como="composicao_por_tipologia.png"):
    variaveis = ["capim", "lenhosa_co", "ruderal", "solo"]
    labels_var = ["Grass Fraction", "Woody Cover", "Weed Fraction", "Bare Soil"]
    ordem = (
        df.groupby(COLUNA_TIPOLOGIA)[COLUNA_ID].nunique()
        .sort_values(ascending=False).index.tolist()
    )

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.subplots_adjust(top=0.88, hspace=0.55, wspace=0.25, bottom=0.12)

    for ax, var, lbl in zip(axes.flat, variaveis, labels_var):
        dados = [df.loc[df[COLUNA_TIPOLOGIA] == cat, var].values for cat in ordem]
        bp = ax.boxplot(dados, patch_artist=True, showfliers=False,
                        medianprops=dict(color="#333333", linewidth=1.5))
        for patch, cat in zip(bp["boxes"], ordem):
            patch.set_facecolor(CORES_Tipologia_.get(cat, "#cccccc"))
            patch.set_alpha(0.75)
            patch.set_edgecolor("#555555")
        ax.set_xticks(range(1, len(ordem) + 1))
        ax.set_xticklabels(ordem, rotation=35, ha="right", fontsize=8.5)
        ax.set_title(lbl, fontsize=11, fontweight="bold", color="#333333")
        aplicar_estilo(ax)

    titulo_subtitulo(fig, "Ground Cover Composition by Typology",
                     "Percentage distribution of grass, woody vegetation, weeds, and bare soil")

    fig.savefig(PASTA_SAIDA / salvar_como, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] {salvar_como}")


# ---------------------------------------------------------------------------
# CHART 3 — Elevation by typology
# ---------------------------------------------------------------------------
def grafico_altitude_por_tipologia(df, salvar_como="altitude_por_tipologia.png"):
    ordem = (
        df.groupby(COLUNA_TIPOLOGIA)[COLUNA_ID].nunique()
        .sort_values(ascending=False).index.tolist()
    )
    dados = [df.loc[df[COLUNA_TIPOLOGIA] == cat, "altitude"].values for cat in ordem]

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.subplots_adjust(top=0.85, bottom=0.28)

    bp = ax.boxplot(dados, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#333333", linewidth=1.5))
    for patch, cat in zip(bp["boxes"], ordem):
        patch.set_facecolor(CORES_Tipologia_.get(cat, "#cccccc"))
        patch.set_alpha(0.75)
        patch.set_edgecolor("#555555")

    ax.set_xticks(range(1, len(ordem) + 1))
    ax.set_xticklabels(ordem, rotation=30, ha="right")
    ax.set_ylabel("Elevation (m)", fontsize=11, color="#333333")

    aplicar_estilo(ax)
    titulo_subtitulo(fig, "Elevation by Typology",
                     "Elevation distribution (meters) for samples in each condition class")

    fig.savefig(PASTA_SAIDA / salvar_como, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] {salvar_como}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = carregar_dados()
    print(f"Dataset loaded: {df.shape[0]:,} rows | typology column: '{COLUNA_TIPOLOGIA}'")

    grafico_amostras_por_classe(df)
    grafico_composicao_por_tipologia(df)
    grafico_altitude_por_tipologia(df)

    print("\nCompleted. PNG figures saved to:", PASTA_SAIDA)
