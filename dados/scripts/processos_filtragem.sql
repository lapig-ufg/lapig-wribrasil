-- ==============================================================================
-- processos_filtragem.sql
-- Pipeline SQL steps for filtering, standardizing, and unifying embeddings
-- ==============================================================================

-- 1. Inspect first MapBiomas dataset
SELECT * FROM 'dados/arquivos_base/embeddings_avg_mapbiomas_pastagem_2019_2025.parquet' LIMIT 10;

-- 2. Inspect MapBiomas 85k dataset
SELECT * FROM 'dados/arquivos_base/embeddings_avg_mapbiomas85k_2019_2025.parquet' LIMIT 100;

-- 3. Element count verification
SELECT COUNT(*) AS total_elementos
FROM 'dados/arquivos_base/mapbiomas_cerrado_pastagem_embeddings_2.parquet';

-- 4. Spatial extension and MapBiomas filtering
INSTALL spatial;
LOAD spatial;

COPY (
    SELECT 
        ID_REVISAO AS id,
        year,
        CLASS_2024 AS class_2025,
        A00, A01, A02, A03, A04, A05, A06, A07, A08, A09,
        A10, A11, A12, A13, A14, A15, A16, A17, A18, A19,
        A20, A21, A22, A23, A24, A25, A26, A27, A28, A29,
        A30, A31, A32, A33, A34, A35, A36, A37, A38, A39,
        A40, A41, A42, A43, A44, A45, A46, A47, A48, A49,
        A50, A51, A52, A53, A54, A55, A56, A57, A58, A59,
        A60, A61, A62, A63,
        LAT AS lat,
        LON As lon,
        ".geo"
    FROM 'dados/arquivos_base/embeddings_avg_mapbiomas85k_2019_2025.parquet'
    WHERE year = 2024 
      AND CLASS_2024 = 'PASTAGEM'
) TO 'dados/arquivos_base/mapbiomas_cerrado_pastagem_embeddings_2.parquet' (FORMAT 'parquet');

-- 5. Assign unique target ID (id_alvo) and unify MapBiomas candidate sets
COPY (
    SELECT 
        ROW_NUMBER() OVER () AS id_alvo,
        * 
    FROM (
        SELECT * FROM 'dados/arquivos_base/mapbiomas_cerrado_pastagem_embeddings_1.parquet'
        UNION ALL
        SELECT * FROM 'dados/arquivos_base/mapbiomas_cerrado_pastagem_embeddings_2.parquet'
    )
) TO 'dados/arquivos_base/mapbiomas_cerrado_pastagem_embeddings_all.parquet' (FORMAT 'parquet');

-- 6. Add field collection survey year (year_colet)
COPY (
    SELECT 
        *,
        EXTRACT(YEAR FROM epoch_ms(CAST(data_colet AS BIGINT))) AS year_colet
    FROM 'dados/arquivos_base/embeddings_avg_training_embrapa_2019_2025_v4.csv'
) TO 'dados/arquivos_base/embeddings_avg_training_embrapa_2019_2025_v5.parquet' (FORMAT 'parquet');

-- 7. Inspect sample feature
SELECT * FROM 'dados/arquivos_base/embeddings_avg_training_embrapa_2019_2025_v5.parquet' LIMIT 1;

-- 8. Filter Embrapa reference points (match collection year with embedding year)
COPY (
    SELECT 
        TARGET_FID,
        Tipologia_,
        TIPOLOGIAc,
        new_class,
        newclassV2,
        year_colet,
        capim,
        lenhosa_co,
        ruderal,
        solo,
        altitude,
        Origem,
        A00, A01, A02, A03, A04, A05, A06, A07, A08, A09,
        A10, A11, A12, A13, A14, A15, A16, A17, A18, A19,
        A20, A21, A22, A23, A24, A25, A26, A27, A28, A29,
        A30, A31, A32, A33, A34, A35, A36, A37, A38, A39,
        A40, A41, A42, A43, A44, A45, A46, A47, A48, A49,
        A50, A51, A52, A53, A54, A55, A56, A57, A58, A59,
        A60, A61, A62, A63,
        latitude AS lat_ref,
        longitude AS lon_ref,
        ".geo"
    FROM 'dados/arquivos_base/embeddings_avg_training_embrapa_2019_2025_v5.parquet'
    WHERE year = year_colet 
) TO 'dados/arquivos_base/embeddings_training_embrapa_2025.parquet' (FORMAT 'parquet');

-- 9. Inspect 701 ground-truth points
SELECT * FROM 'dados/arquivos_base/embeddings_training_embrapa_2025.parquet' LIMIT 701;
