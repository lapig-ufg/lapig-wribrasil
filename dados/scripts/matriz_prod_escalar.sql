-- ==============================================================================
-- matriz_prod_escalar.sql
-- Generates dense similarity matrix via DuckDB PIVOT (Dot Product across 64 dimensions)
-- ==============================================================================

COPY (
    PIVOT (
        SELECT 
            -- 64-dimensional Dot Product Computation
            (e.A00 * m.A00 + e.A01 * m.A01 + e.A02 * m.A02 + e.A03 * m.A03 + 
             e.A04 * m.A04 + e.A05 * m.A05 + e.A06 * m.A06 + e.A07 * m.A07 + 
             e.A08 * m.A08 + e.A09 * m.A09 + e.A10 * m.A10 + e.A11 * m.A11 + 
             e.A12 * m.A12 + e.A13 * m.A13 + e.A14 * m.A14 + e.A15 * m.A15 + 
             e.A16 * m.A16 + e.A17 * m.A17 + e.A18 * m.A18 + e.A19 * m.A19 + 
             e.A20 * m.A20 + e.A21 * m.A21 + e.A22 * m.A22 + e.A23 * m.A23 + 
             e.A24 * m.A24 + e.A25 * m.A25 + e.A26 * m.A26 + e.A27 * m.A27 + 
             e.A28 * m.A28 + e.A29 * m.A29 + e.A30 * m.A30 + e.A31 * m.A31 + 
             e.A32 * m.A32 + e.A33 * m.A33 + e.A34 * m.A34 + e.A35 * m.A35 + 
             e.A36 * m.A36 + e.A37 * m.A37 + e.A38 * m.A38 + e.A39 * m.A39 + 
             e.A40 * m.A40 + e.A41 * m.A41 + e.A42 * m.A42 + e.A43 * m.A43 + 
             e.A44 * m.A44 + e.A45 * m.A45 + e.A46 * m.A46 + e.A47 * m.A47 + 
             e.A48 * m.A48 + e.A49 * m.A49 + e.A50 * m.A50 + e.A51 * m.A51 + 
             e.A52 * m.A52 + e.A53 * m.A53 + e.A54 * m.A54 + e.A55 * m.A55 + 
             e.A56 * m.A56 + e.A57 * m.A57 + e.A58 * m.A58 + e.A59 * m.A59 + 
             e.A60 * m.A60 + e.A61 * m.A61 + e.A62 * m.A62 + e.A63 * m.A63) AS produto_escalar,
            m.id_alvo AS id_mapbiomas,
            e.TARGET_FID
             
        -- Filtered input tables
        FROM read_parquet('dados/arquivos_base/embeddings_training_embrapa_2025.parquet') AS e
        CROSS JOIN read_parquet('dados/arquivos_base/mapbiomas_cerrado_pastagem_embeddings_all.parquet') AS m
    )
    ON TARGET_FID 
    USING MAX(produto_escalar)
    
) TO 'dados/arquivos_saida/matriz_similaridade_embrapa_mapbiomas_2025.parquet' (FORMAT PARQUET);
