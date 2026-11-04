-- ==============================================================================
-- filtro_prod_escalar.sql
-- Filters Top-3 highest dot product matches per target pixel (id_alvo) via QUALIFY
-- ==============================================================================

COPY (
    SELECT *
    FROM read_parquet('dados/arquivos_saida/prod_escalar_embrapa_mapbiomas.parquet')
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY id_alvo
        ORDER BY prod_escalar DESC
    ) <= 3
) TO 'dados/arquivos_saida/top3_prod_escalar_por_mapbiomas.parquet' (FORMAT PARQUET);
