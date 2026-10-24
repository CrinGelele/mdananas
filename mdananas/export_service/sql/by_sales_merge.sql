CREATE OR ALTER PROCEDURE [15_BY].[BY_PROC_MERGE_Sales]
AS
BEGIN
    -- Загружаем продажи только за 2027 год.
    IF EXISTS (
        SELECT 1 FROM [15_BY].[BY_STAGE_Sales_Draft]
        WHERE TRY_CONVERT(int, date_year) IS NULL
           OR TRY_CONVERT(int, date_year) <> 2027
    )
        THROW 51100, N'Разрешена загрузка продаж только за 2027 год.', 1;

    MERGE [15_BY].[BY_PIVOT_SKU] BASE USING (
        SELECT material, MIN(material_desc) by_description
        FROM [15_BY].[BY_STAGE_Sales_Draft]
        GROUP BY material
    ) TMP ON BASE.material = TMP.material
    WHEN NOT MATCHED THEN INSERT (
        material, by_description
    ) VALUES (
        TMP.material, TMP.by_description
    );

    MERGE [15_BY].[BY_REF_Stores] BASE USING (
        SELECT DISTINCT store_by FROM [15_BY].[BY_STAGE_Sales_Draft]
    ) TMP ON BASE.store_by = TMP.store_by
         OR BASE.store_by = N'"' + REPLACE(TMP.store_by, N'"', N'""') + N'"'
    WHEN NOT MATCHED THEN INSERT (
        store_by
    ) VALUES (
        TMP.store_by
    );

    MERGE [15_BY].[BY_DATA_Sales] BASE USING (
        SELECT CAST(A.date_year AS smallint) date_year,
               CAST(A.date_month AS tinyint) date_month,
               B.id by_store_id, C.id by_pivot_sku_id,
               SUM(CAST(A.volume AS float)) volume,
               SUM(CAST(A.purchase_price_value AS float)) purchase_price_value,
               SUM(CAST(A.fact_price_value AS float)) fact_price_value
        FROM [15_BY].[BY_STAGE_Sales_Draft] A
        LEFT JOIN [15_BY].[BY_REF_Stores] B
            ON B.store_by = A.store_by
            OR B.store_by = N'"' + REPLACE(A.store_by, N'"', N'""') + N'"'
        LEFT JOIN [15_BY].[BY_PIVOT_SKU] C ON C.material = A.material
        GROUP BY A.date_year, A.date_month, B.id, C.id
    ) TMP ON BASE.date_year = 2027
         AND BASE.date_year = TMP.date_year
         AND BASE.date_month = TMP.date_month
         AND BASE.by_store_id = TMP.by_store_id
         AND BASE.by_pivot_sku_id = TMP.by_pivot_sku_id
    WHEN MATCHED THEN UPDATE SET
        volume = TMP.volume,
        purchase_price_value = TMP.purchase_price_value,
        fact_price_value = TMP.fact_price_value
    WHEN NOT MATCHED THEN INSERT (
        date_year, date_month, by_store_id, by_pivot_sku_id,
        volume, purchase_price_value, fact_price_value
    ) VALUES (
        TMP.date_year, TMP.date_month, TMP.by_store_id, TMP.by_pivot_sku_id,
        TMP.volume, TMP.purchase_price_value, TMP.fact_price_value
    );
    -- Отмечаем SKU из последней загрузки.
    UPDATE P
    SET is_last_upload = CASE
        WHEN EXISTS (
            SELECT 1
            FROM [15_BY].[BY_STAGE_Sales_Draft] S
            WHERE S.material = P.material
        ) THEN 1
        ELSE 0
    END
    FROM [15_BY].[BY_PIVOT_SKU] P;
END;
GO
