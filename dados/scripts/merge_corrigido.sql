-- ==============================================================================
-- merge_corrigido.sql
-- Spatial merge and reconciliation of agricultural/pasture field samples in GeoPackage
-- ==============================================================================

-- 1. Activate spatial extension (if not already active in session)
INSTALL spatial;
LOAD spatial;

-- Force coordinate axis order to [Longitude, Latitude] to prevent coordinate inversion
SET geometry_always_xy = true;

-- 2. Execute merge copy
COPY (
    SELECT 
        -- 1. Reconcile merged attributes with COALESCE across parts
        COALESCE(t1.IDs, t2.IDs) AS IDs,
        COALESCE(t1.tipo_amostra, t2.tipo_amostra) AS tipo_amostra,
        COALESCE(t1.tipo_integ, t2.tipo_integ) AS tipo_integ,
        COALESCE(t1."1_cult_ini", t2."1_cult_ini") AS "1_cult_ini",
        COALESCE(t1."1_cult_fim", t2."1_cult_fim") AS "1_cult_fim",
        COALESCE(t1."2_cult_ini", t2."2_cult_ini") AS "2_cult_ini",
        COALESCE(t1."2_cult_fim", t2."2_cult_fim") AS "2_cult_fim",
        COALESCE(t1.pasture_in, t2.pasture_in) AS pasture_in,
        COALESCE(t1.pasture_fi, t2.pasture_fi) AS pasture_fi,
        COALESCE(t1.geom, t2.geom) AS geom,

        -- 2. Select remaining attributes from primary file (t1),
        -- excluding columns already coalesced and internal fid to allow driver autoincrement
        t1.* EXCLUDE (
            fid,
            IDs, tipo_amostra, tipo_integ, 
            "1_cult_ini", "1_cult_fim", 
            "2_cult_ini", "2_cult_fim", 
            pasture_in, pasture_fi, geom
        )

    -- Read primary layer
    FROM st_read('dados/arquivos_base/sem_sobreposicao_ordenado_4326_merged.gpkg') t1

    -- Full outer join on unique ID key
    FULL OUTER JOIN st_read('dados/arquivos_base/sem_sobreposicao_ordenado_4326_v_poli.gpkg') t2 
      ON t1.IDs = t2.IDs

    -- 3. Filter out orphan features lacking ID in both inputs
    WHERE COALESCE(t1.IDs, t2.IDs) IS NOT NULL

-- Export cleaned GeoPackage using GDAL driver
) TO 'dados/arquivos_saida/amostras_ilpf_inspecionadas_4326.gpkg' 
WITH (FORMAT GDAL, DRIVER 'GPKG');
