"""
pipeline_filtrado_pastagem_75.py
=================================
Processing pipeline filtered specifically for Pasture sample points
(class_2025 = 15) with a dot product threshold cutoff of >= 0.75 (75%).

Outputs generated in: arquivos_saida/filtrado_50k_pastagem/
  1. matriz_similaridade_50k_pastagem_75.parquet
     - Dense pivoted matrix (44,943 rows x 705 columns) with values < 0.75 set to NaN.
  2. tabela_top3_pivotada_50k_pastagem_75.parquet
     - Table with the 3 best matches (>= 0.75), suffixes _1, _2, _3, class_embrapa and md3.
  3. pontos_por_class_embrapa_md3.png
     - Figure with colored Embrapa class bar (totalizer label) and adjacent
       3-shade gray bar normalized to 100% (md3 = 1, 2, 3 agreement).
  4. pontos_por_class_embrapa.png
     - Simple bar chart counting points per Embrapa typology.
  5. resumo_contagem_pastagem_75.csv
     - Summary table of points and matches by threshold.

Usage:
    python pipeline_filtrado_pastagem_75.py
"""

import duckdb
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

# ----------------------------------------------------------------
# Paths and Arguments
# ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Filtered pasture pipeline (threshold 75%).")
parser.add_argument("--year", default="2025", help="Year to analyze (default: 2025).")
args = parser.parse_args()
ANO = args.year

DIR_SCRIPTS = Path(__file__).resolve().parent
DIR_ROOT = DIR_SCRIPTS.parent
DIR_METRICAS = DIR_ROOT / "produto_escalar_metricas"
DIR_SAIDA_BASE = DIR_METRICAS / "arquivos_saida"
DIR_SAIDA_FILTRADO = DIR_SAIDA_BASE / "filtrado_50k_pastagem"
DIR_SAIDA_FILTRADO.mkdir(parents=True, exist_ok=True)

PARQUET_PROD_ESCALAR = DIR_METRICAS / f"prod_escalar_50k_{ANO}.parquet"
if not PARQUET_PROD_ESCALAR.exists():
    alt = DIR_METRICAS / "prod_escalar_50k_serie_completa.parquet"
    if alt.exists():
        PARQUET_PROD_ESCALAR = alt
    else:
        alt2 = DIR_SAIDA_BASE / "prod_escalar_50k_serie_completa.parquet"
        if alt2.exists():
            PARQUET_PROD_ESCALAR = alt2

PARQUET_MATRIZ_ORIG = DIR_SAIDA_BASE / f"matriz_similaridade_50k_{ANO}.parquet"
if not PARQUET_MATRIZ_ORIG.exists():
    alt_m = DIR_SAIDA_BASE / "matriz_similaridade_50k.parquet"
    if alt_m.exists():
        PARQUET_MATRIZ_ORIG = alt_m

PARQUET_MATRIZ_75 = DIR_SAIDA_FILTRADO / f"matriz_similaridade_50k_pastagem_75_{ANO}.parquet"
PARQUET_TOP3_75 = DIR_SAIDA_FILTRADO / f"tabela_top3_pivotada_50k_pastagem_75_{ANO}.parquet"
CSV_RESUMO = DIR_SAIDA_FILTRADO / f"resumo_contagem_pastagem_75_{ANO}.csv"

# ----------------------------------------------------------------
# Official Embrapa Color Palette
# ----------------------------------------------------------------
CORES_TIPOLOGIA = {
    "PASTO PRODUTIVO": "#faea40",
    "PASTO COM ERVAS": "#d8ff6c",
    "REG NATURAL": "#0e5f0e",
    "INTERMEDIARIO": "#f4b346",
    "DEG BIOLOGICA": "#813209",
    "PASTO COM LENHOSAS": "#66c600",
    "MISCELANEA": "#ec2b10",
    "Desconhecido": "#cccccc"
}

VALORES_EXCLUIR = {"Desconhecido", "Não Classificado", "Outros", "N/A", "nan", ""}


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
    fig.text(0.08, 0.95, titulo,
             fontsize=14, fontweight="bold", color="#111111",
             ha="left", va="top")
    fig.text(0.08, 0.90, subtitulo,
             fontsize=9.5, color="#666666",
             ha="left", va="top")


# ================================================================
# 1. Generate Pivoted Similarity Matrix (Pasture + Threshold 0.75)
# ================================================================
def gerar_matriz_similaridade_pastagem_75(con):
    print("\n" + "=" * 70)
    print("STEP 1: GENERATING PIVOTED SIMILARITY MATRIX (PASTURE >= 0.75)")
    print("=" * 70)
    print(f"  Source: {PARQUET_MATRIZ_ORIG.name}")
    print(f"  Filter: class_2025 = 15 AND threshold >= 0.75 (values < 0.75 -> NaN)")
    print(f"  Output: {PARQUET_MATRIZ_75.name}")

    t0 = time.time()

    # Get list of TARGET_FID columns (all except the 4 metadata columns)
    df_sample = con.execute(f"SELECT * FROM '{PARQUET_MATRIZ_ORIG}' LIMIT 1").df()
    meta_cols = ["id", "class_cvp", "class_2025", "stable_20_"]
    target_cols = [c for c in df_sample.columns if c not in meta_cols]

    print(f"  Total TARGET_FID target columns: {len(target_cols)}")

    case_exprs = []
    for c in target_cols:
        case_exprs.append(f'CASE WHEN "{c}" >= 0.75 THEN "{c}" ELSE NULL END AS "{c}"')

    select_sql = f"""
        SELECT 
            id, class_cvp, class_2025, stable_20_,
            {', '.join(case_exprs)}
        FROM '{PARQUET_MATRIZ_ORIG}'
        WHERE class_2025 = 15
    """

    con.execute(f"""
        COPY ({select_sql}) TO '{PARQUET_MATRIZ_75}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """)

    dt = time.time() - t0
    n_linhas = con.execute(f"SELECT count(*) FROM '{PARQUET_MATRIZ_75}'").fetchone()[0]
    print(f"  [OK] Matrix generated in {dt:.1f}s with {n_linhas:,} rows.")


# ================================================================
# 2. Generate Pivoted Top-3 Table with MD3 (Pasture + Threshold 0.75)
# ================================================================
def gerar_top3_pivotada_pastagem_75(con):
    print("\n" + "=" * 70)
    print("STEP 2: GENERATING PIVOTED TOP-3 TABLE WITH MD3 (PASTURE >= 0.75)")
    print("=" * 70)
    print(f"  Filter: class_2025 = 15 AND prod_escalar_1 >= 0.75")
    print(f"  Output: {PARQUET_TOP3_75.name}")

    t0 = time.time()

    parquet_top3_in = DIR_SAIDA_BASE / f"tabela_top3_pivotada_50k_{ANO}.parquet"
    if not parquet_top3_in.exists():
        parquet_top3_in = DIR_SAIDA_BASE / "tabela_top3_pivotada_50k.parquet"

    if parquet_top3_in.exists():
        query = f"""
        COPY (
            SELECT * 
            FROM '{parquet_top3_in}'
            WHERE class_2025 = 15 AND prod_escalar_1 >= 0.75
            ORDER BY id
        ) TO '{PARQUET_TOP3_75}' (FORMAT PARQUET)
        """
    else:
        query = f"""
        COPY (
            WITH filtrado AS (
                SELECT
                    id,
                    TARGET_FID,
                    MAX(resultado_multiplicacao) AS resultado_multiplicacao,
                    FIRST(Origem) AS Origem,
                    FIRST(TIPOLOGIAc) AS TIPOLOGIAc,
                    FIRST(Tipologia_) AS Tipologia_,
                    FIRST(altitude) AS altitude,
                    FIRST(capim) AS capim,
                    FIRST(lenhosa_co) AS lenhosa_co,
                    FIRST(ruderal) AS ruderal,
                    FIRST(solo) AS solo,
                    FIRST(lat_ref) AS lat_ref,
                    FIRST(lon_ref) AS lon_ref,
                    FIRST(class_cvp) AS class_cvp,
                    FIRST(class_2025) AS class_2025,
                    FIRST(stable_20_) AS stable_20_
                FROM '{PARQUET_PROD_ESCALAR}'
                WHERE class_2025 = 15
                  AND resultado_multiplicacao >= 0.75
                GROUP BY id, TARGET_FID
            ),
            ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY id
                    ORDER BY resultado_multiplicacao DESC
                ) AS rn
            FROM filtrado
        ),
        top3 AS (
            SELECT * FROM ranked WHERE rn <= 3
        ),
        pivotado AS (
            SELECT
                id,
                MAX(class_cvp) AS class_cvp,
                MAX(class_2025) AS class_2025,
                MAX(stable_20_) AS stable_20_,
                
                -- TOP 1
                MAX(CASE WHEN rn = 1 THEN TARGET_FID END) AS target_fid_1,
                MAX(CASE WHEN rn = 1 THEN resultado_multiplicacao END) AS prod_escalar_1,
                MAX(CASE WHEN rn = 1 THEN Origem END) AS origem_1,
                MAX(CASE WHEN rn = 1 THEN TIPOLOGIAc END) AS tipologia_c_1,
                MAX(CASE WHEN rn = 1 THEN Tipologia_ END) AS tipologia_1,
                MAX(CASE WHEN rn = 1 THEN capim END) AS capim_1,
                MAX(CASE WHEN rn = 1 THEN lenhosa_co END) AS lenhosa_co_1,
                MAX(CASE WHEN rn = 1 THEN ruderal END) AS ruderal_1,
                MAX(CASE WHEN rn = 1 THEN solo END) AS solo_1,
                MAX(CASE WHEN rn = 1 THEN altitude END) AS altitude_1,
                MAX(CASE WHEN rn = 1 THEN concat(CAST(lat_ref AS VARCHAR), ', ', CAST(lon_ref AS VARCHAR)) END) AS loc_1,
                MAX(CASE WHEN rn = 1 THEN class_cvp END) AS class_cvp_1,
                MAX(CASE WHEN rn = 1 THEN class_2025 END) AS class_2025_1,
                MAX(CASE WHEN rn = 1 THEN stable_20_ END) AS stable_20_1,

                -- TOP 2
                MAX(CASE WHEN rn = 2 THEN TARGET_FID END) AS target_fid_2,
                MAX(CASE WHEN rn = 2 THEN resultado_multiplicacao END) AS prod_escalar_2,
                MAX(CASE WHEN rn = 2 THEN Origem END) AS origem_2,
                MAX(CASE WHEN rn = 2 THEN TIPOLOGIAc END) AS tipologia_c_2,
                MAX(CASE WHEN rn = 2 THEN Tipologia_ END) AS tipologia_2,
                MAX(CASE WHEN rn = 2 THEN capim END) AS capim_2,
                MAX(CASE WHEN rn = 2 THEN lenhosa_co END) AS lenhosa_co_2,
                MAX(CASE WHEN rn = 2 THEN ruderal END) AS ruderal_2,
                MAX(CASE WHEN rn = 2 THEN solo END) AS solo_2,
                MAX(CASE WHEN rn = 2 THEN altitude END) AS altitude_2,
                MAX(CASE WHEN rn = 2 THEN concat(CAST(lat_ref AS VARCHAR), ', ', CAST(lon_ref AS VARCHAR)) END) AS loc_2,
                MAX(CASE WHEN rn = 2 THEN class_cvp END) AS class_cvp_2,
                MAX(CASE WHEN rn = 2 THEN class_2025 END) AS class_2025_2,
                MAX(CASE WHEN rn = 2 THEN stable_20_ END) AS stable_20_2,

                -- TOP 3
                MAX(CASE WHEN rn = 3 THEN TARGET_FID END) AS target_fid_3,
                MAX(CASE WHEN rn = 3 THEN resultado_multiplicacao END) AS prod_escalar_3,
                MAX(CASE WHEN rn = 3 THEN Origem END) AS origem_3,
                MAX(CASE WHEN rn = 3 THEN TIPOLOGIAc END) AS tipologia_c_3,
                MAX(CASE WHEN rn = 3 THEN Tipologia_ END) AS tipologia_3,
                MAX(CASE WHEN rn = 3 THEN capim END) AS capim_3,
                MAX(CASE WHEN rn = 3 THEN lenhosa_co END) AS lenhosa_co_3,
                MAX(CASE WHEN rn = 3 THEN ruderal END) AS ruderal_3,
                MAX(CASE WHEN rn = 3 THEN solo END) AS solo_3,
                MAX(CASE WHEN rn = 3 THEN altitude END) AS altitude_3,
                MAX(CASE WHEN rn = 3 THEN concat(CAST(lat_ref AS VARCHAR), ', ', CAST(lon_ref AS VARCHAR)) END) AS loc_3,
                MAX(CASE WHEN rn = 3 THEN class_cvp END) AS class_cvp_3,
                MAX(CASE WHEN rn = 3 THEN class_2025 END) AS class_2025_3,
                MAX(CASE WHEN rn = 3 THEN stable_20_ END) AS stable_20_3

            FROM top3
            GROUP BY id
        ),
        final AS (
            SELECT
                *,
                tipologia_1 AS class_embrapa,
                1 +
                CASE WHEN tipologia_2 = tipologia_1 THEN 1 ELSE 0 END +
                CASE WHEN tipologia_3 = tipologia_1 THEN 1 ELSE 0 END AS md3
            FROM pivotado
        )
        SELECT * FROM final
        ORDER BY id
    ) TO '{PARQUET_TOP3_75}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """

    con.execute(query)
    dt = time.time() - t0

    n_final = con.execute(f"SELECT count(*) FROM '{PARQUET_TOP3_75}'").fetchone()[0]
    print(f"  [OK] Top-3 table generated in {dt:.1f}s with {n_final:,} points.")


# ================================================================
# 3. Generate Charts and Summary Report
# ================================================================
def gerar_graficos_e_resumos():
    print("\n" + "=" * 70)
    print("STEP 3: GENERATING CHARTS AND SUMMARY (PASTURE >= 0.75)")
    print("=" * 70)

    df = pd.read_parquet(PARQUET_TOP3_75)
    df = df[~df["class_embrapa"].isin(VALORES_EXCLUIR)].copy()
    total_pontos = len(df)
    print(f"  Total valid pasture points with threshold >= 0.75: {total_pontos:,}")

    contagem_classes = df["class_embrapa"].value_counts()
    ordem = contagem_classes.index.tolist()
    cores = {tip: CORES_TIPOLOGIA.get(tip, "#cccccc") for tip in ordem}

    # -------------------------------------------------------------
    # 3.1. Chart 1: MapBiomas points by class_embrapa (Simple)
    # -------------------------------------------------------------
    print("  [1/2] Generating simple point count chart by class...")
    fig, ax = plt.subplots(figsize=(11, 7))
    fig.subplots_adjust(top=0.82, bottom=0.22)

    barras = ax.bar(range(len(ordem)), contagem_classes.values,
                    color=[cores[t] for t in ordem],
                    width=0.65, zorder=3, edgecolor="white", linewidth=0.5)

    for barra, valor in zip(barras, contagem_classes.values):
        pct = valor / total_pontos * 100
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
        "Classification of MapBiomas Pasture Points (Threshold >= 0.75)",
        f"{total_pontos:,} pasture points (class_2025 = 15) classified by highest dot-product TARGET_FID")

    caminho1 = DIR_SAIDA_FILTRADO / "pontos_por_class_embrapa.png"
    fig.savefig(caminho1, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    [ok] {caminho1.name}")

    # -------------------------------------------------------------
    # 3.2. Chart 2: MD3 agreement composition by class (Gray Bars)
    # -------------------------------------------------------------
    print("  [2/2] Generating chart with grayscale MD3 agreement composition...")

    pct_md3_1, pct_md3_2, pct_md3_3 = [], [], []
    for t in ordem:
        sub = df[df["class_embrapa"] == t]
        tot = len(sub)
        if tot > 0:
            pct_md3_1.append((sub["md3"] == 1).sum() / tot * 100)
            pct_md3_2.append((sub["md3"] == 2).sum() / tot * 100)
            pct_md3_3.append((sub["md3"] == 3).sum() / tot * 100)
        else:
            pct_md3_1.append(0)
            pct_md3_2.append(0)
            pct_md3_3.append(0)

    pct_md3_1 = np.array(pct_md3_1)
    pct_md3_2 = np.array(pct_md3_2)
    pct_md3_3 = np.array(pct_md3_3)

    fig, ax = plt.subplots(figsize=(13, 8))
    fig.subplots_adjust(top=0.74, bottom=0.20, left=0.08, right=0.95)

    x = np.arange(len(ordem))
    width = 0.35

    barras_total = ax.bar(x - width/2, [100] * len(ordem),
                          color=[cores[t] for t in ordem],
                          width=width, zorder=3, edgecolor="white", linewidth=0.5,
                          label="Class Identifier")

    ax.bar(x + width/2, pct_md3_1, width=width, color="#d9d9d9",
           edgecolor="white", linewidth=0.5, zorder=3, label="md3 = 1 (No agreement)")
    ax.bar(x + width/2, pct_md3_2, bottom=pct_md3_1, width=width, color="#969696",
           edgecolor="white", linewidth=0.5, zorder=3, label="md3 = 2 (1 of 2 agree)")
    ax.bar(x + width/2, pct_md3_3, bottom=pct_md3_1 + pct_md3_2, width=width, color="#525252",
           edgecolor="white", linewidth=0.5, zorder=3, label="md3 = 3 (All 3 agree)")

    for barra, valor in zip(barras_total, contagem_classes.values):
        pct = valor / total_pontos * 100
        ax.text(barra.get_x() + barra.get_width() / 2,
                102,
                f"{valor:,}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=8.5,
                color="#222222", fontweight="bold")

    for i in range(len(ordem)):
        tot = contagem_classes.values[i]
        if tot == 0:
            continue
        p1 = pct_md3_1[i]
        if p1 > 4.0:
            ax.text(x[i] + width/2, p1 / 2, f"{p1:.0f}%",
                    ha="center", va="center", fontsize=8.5, color="#222222", fontweight="bold")
        p2 = pct_md3_2[i]
        if p2 > 4.0:
            ax.text(x[i] + width/2, p1 + p2 / 2, f"{p2:.0f}%",
                    ha="center", va="center", fontsize=8.5, color="#ffffff", fontweight="bold")
        p3 = pct_md3_3[i]
        if p3 > 4.0:
            ax.text(x[i] + width/2, p1 + p2 + p3 / 2, f"{p3:.0f}%",
                    ha="center", va="center", fontsize=8.5, color="#ffffff", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(ordem, rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("Agreement Proportion (%)", fontsize=11, color="#333333")
    ax.set_xlabel("Embrapa Reference Class (Top-1 Typology)", fontsize=11, color="#333333")
    ax.set_ylim(0, 115)

    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.03), ncol=4, fontsize=9,
              frameon=True, facecolor="white", edgecolor="#d0d0d0", framealpha=1.0)

    estilo_limpo(ax)
    titulo_subtitulo(fig,
        "Agreement Composition (md3) for MapBiomas Pasture (Threshold >= 0.75)",
        f"{total_pontos:,} pasture points (class_2025 = 15). Colored bar = class total; Gray bar = internal md3 agreement")

    caminho2 = DIR_SAIDA_FILTRADO / "pontos_por_class_embrapa_md3.png"
    fig.savefig(caminho2, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    [ok] {caminho2.name}")

    # -------------------------------------------------------------
    # 3.3. Chart 3: Donut chart of CVP vigor index by Embrapa class
    # -------------------------------------------------------------
    print("  [3/3] Generating donut chart (CVP vigor on outer ring + center class color)...")
    from matplotlib.patches import Patch, Circle

    CORES_CVP = {
        1: "#d73027", # Low Vigor (Red)
        2: "#f4a582", # Medium Vigor (Orange/Salmon)
        3: "#1a9850"  # High Vigor (Green)
    }

    fig, axes = plt.subplots(2, 4, figsize=(16, 9))
    fig.subplots_adjust(top=0.88, bottom=0.08, left=0.04, right=0.96, hspace=0.35, wspace=0.25)
    axes_flat = axes.flatten()

    for i, classe in enumerate(ordem):
        ax = axes_flat[i]
        sub = df[df["class_embrapa"] == classe]
        cvp_counts = sub["class_cvp"].value_counts().sort_index()
        valores = [cvp_counts.get(k, 0) for k in [1, 2, 3]]
        cores_pie = [CORES_CVP[k] for k in [1, 2, 3]]

        ax.pie(valores, colors=cores_pie, radius=1.0,
               wedgeprops=dict(width=0.35, edgecolor='white', linewidth=1.5),
               startangle=90)

        # Center circle colored by Embrapa class
        circle = Circle((0, 0), 0.65, color=cores[classe], ec='white', lw=1.5)
        ax.add_artist(circle)

        total_cls = len(sub)
        pct_cls = (total_cls / total_pontos) * 100
        ax.set_title(f"{classe}\n(n={total_cls:,} | {pct_cls:.1f}%)",
                     fontsize=10.5, fontweight='bold', color='#222222', pad=8)

    # Empty final subplot used for legend
    ax_leg = axes_flat[-1]
    ax_leg.axis('off')

    legend_elements_cvp = [
        Patch(facecolor=CORES_CVP[1], edgecolor='white', label='Low Vigor (CVP 1)'),
        Patch(facecolor=CORES_CVP[2], edgecolor='white', label='Medium Vigor (CVP 2)'),
        Patch(facecolor=CORES_CVP[3], edgecolor='white', label='High Vigor (CVP 3)')
    ]

    ax_leg.text(0.1, 0.85, "• Outer Ring: Vigor Classes (CVP 1, 2, 3)", fontsize=9.5, color="#333333", transform=ax_leg.transAxes)
    ax_leg.text(0.1, 0.77, "• Center: Embrapa Reference Class Color", fontsize=9.5, color="#333333", transform=ax_leg.transAxes)
    ax_leg.text(0.1, 0.69, "• Header: Class Name and Sample Count (n)", fontsize=9.5, color="#333333", transform=ax_leg.transAxes)

    ax_leg.legend(handles=legend_elements_cvp, loc="center left", bbox_to_anchor=(0.08, 0.35),
                  title="Vigor Index (Sentinel-2)", fontsize=9.5, title_fontsize=10.5,
                  frameon=True, facecolor="#fbfbfb", edgecolor="#d0d0d0")

    fig.suptitle("Vigor Index Distribution (class_cvp) by Embrapa Class - Pasture (Threshold >= 0.75)",
                 fontsize=14, fontweight='bold', y=0.96)

    caminho3 = DIR_SAIDA_FILTRADO / "pizza_cvp_por_classe_embrapa.png"
    fig.savefig(caminho3, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"    [ok] {caminho3.name}")

    # -------------------------------------------------------------
    # 3.4. Save Summary CSV
    # -------------------------------------------------------------
    df_resumo = df.groupby(["class_embrapa", "md3"]).size().unstack(fill_value=0)
    df_resumo["Total"] = df_resumo.sum(axis=1)
    df_resumo["% of Total"] = (df_resumo["Total"] / total_pontos) * 100
    df_resumo.to_csv(CSV_RESUMO)
    print(f"  [ok] Statistical summary saved to {CSV_RESUMO.name}")


def main():
    print("=" * 70)
    print("FILTERED PIPELINE: 50K PASTURE (class_2025 = 15) WITH THRESHOLD >= 0.75")
    print("=" * 70)

    con = duckdb.connect()

    # 1. Pivoted Similarity Matrix
    gerar_matriz_similaridade_pastagem_75(con)

    # 2. Pivoted Top-3 Table with MD3
    gerar_top3_pivotada_pastagem_75(con)

    # 3. Charts and Visualizations
    gerar_graficos_e_resumos()

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"Files saved in: {DIR_SAIDA_FILTRADO}")
    print("=" * 70)


if __name__ == "__main__":
    main()
