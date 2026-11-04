-- ==============================================================================
-- salvar_csv_corrigir_lat_long.sql
-- Exports CSV correcting coordinate inversion (lon_alvo <-> lat_alvo) for Pasture
-- ==============================================================================

COPY (
    SELECT 
        id_alvo,
        class_2025,
        class_embrapa,
        md3,
        
        -- Inversion correction for latitude
        CASE 
            WHEN class_2025 = 'Pastagem' THEN lon_alvo 
            ELSE lat_alvo 
        END AS lat_alvo,
        
        -- Inversion correction for longitude
        CASE 
            WHEN class_2025 = 'Pastagem' THEN lat_alvo 
            ELSE lon_alvo 
        END AS lon_alvo,
        
        target_fid_1,
        prod_escalar_1,
        id_1,
        origem_1,
        tipologia_c_1,
        tipologia_1,
        new_class_1,
        newclassv2_1,
        capim_1,
        lenhosa_co_1,
        ruderal_1,
        solo_1,
        altitude_1,
        year_colet_1,
        loc_1,
        target_fid_2,
        prod_escalar_2,
        id_2,
        origem_2,
        tipologia_c_2,
        tipologia_2,
        new_class_2,
        newclassv2_2,
        capim_2,
        lenhosa_co_2,
        ruderal_2,
        solo_2,
        altitude_2,
        year_colet_2,
        loc_2,
        target_fid_3,
        prod_escalar_3,
        id_3,
        origem_3,
        tipologia_c_3,
        tipologia_3,
        new_class_3,
        newclassv3_3,
        capim_3,
        lenhosa_co_3,
        ruderal_3,
        solo_3,
        altitude_3,
        year_colet_3,
        loc_3

    FROM 'dados/arquivos_saida/tabela_top3_pivotada.parquet'
) TO 'dados/arquivos_saida/tabela_top3_pivotada.csv' (FORMAT 'csv', HEADER true);
