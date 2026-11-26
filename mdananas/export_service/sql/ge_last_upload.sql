-- Периоды последней выгрузки продаж и остатков по товарам.
IF COL_LENGTH(N'dbo.GE_PIVOT_SKU', N'last_sales_period') IS NULL
    ALTER TABLE dbo.GE_PIVOT_SKU ADD last_sales_period date NULL;
IF COL_LENGTH(N'dbo.GE_PIVOT_SKU', N'last_stock_period') IS NULL
    ALTER TABLE dbo.GE_PIVOT_SKU ADD last_stock_period date NULL;
GO

ALTER PROCEDURE [dbo].[GE_PROC_MERGE_Sales] (@path nvarchar(100))
AS
BEGIN
    SET XACT_ABORT ON;

    DECLARE @sql nvarchar(500);
    CREATE TABLE #tmp_ge_sales (
        eng nvarchar(250),
        [date] nvarchar(250),
        materialge nvarchar(250) COLLATE DATABASE_DEFAULT,
        sales nvarchar(250),
        [value] nvarchar(250),
        store_no nvarchar(250) COLLATE DATABASE_DEFAULT
    );

    SET @sql = N'BULK INSERT #tmp_ge_sales FROM '''
             + REPLACE(@path, N'''', N'''''')
             + N''' WITH (CODEPAGE = ''65001'', FIRSTROW = 2,
                          FIELDTERMINATOR = '';'', ROWTERMINATOR = ''\n'')';
    EXEC(@sql);

    DELETE FROM #tmp_ge_sales
    WHERE materialge IS NULL AND store_no IS NULL AND eng IS NULL;

    DECLARE @own_transaction bit = CASE WHEN @@TRANCOUNT = 0 THEN 1 ELSE 0 END;
    BEGIN TRY
        IF @own_transaction = 1 BEGIN TRANSACTION;

        -- Продажи и остатки могут одновременно пополнять одни и те же позиции.
        MERGE dbo.GE_PIVOT_SKU WITH (TABLOCKX) AS BASE
        USING (SELECT DISTINCT materialge FROM #tmp_ge_sales) AS TMP
            ON BASE.material = TMP.materialge
        WHEN NOT MATCHED THEN
            INSERT (material) VALUES (TMP.materialge);

        MERGE dbo.GE_PIVOT_Stores AS BASE
        USING (SELECT DISTINCT store_no FROM #tmp_ge_sales) AS TMP
            ON BASE.store_ge = TMP.store_no
        WHEN NOT MATCHED THEN
            INSERT (store_ge) VALUES (TMP.store_no);

        DECLARE @loaded TABLE (sku_id int, period date);

        MERGE dbo.GE_DATA_Sales AS BASE
        USING (
            SELECT B.id AS ge_pivot_sku_id, C.id AS ge_pivot_store_id,
                   YEAR(A.[date]) AS date_year, MONTH(A.[date]) AS date_month,
                   DATEPART(week, A.[date]) AS date_week, DAY(A.[date]) AS date_day,
                   SUM(A.sales) AS sales,
                   SUM(A.[value]) AS [value]
            FROM (
                SELECT TRY_PARSE(REPLACE([date], '''', '') AS date USING 'de-DE') AS [date],
                       materialge, store_no,
                       CAST(REPLACE(REPLACE(sales, ' ', ''), ',', '.') AS real) AS sales,
                       CAST(REPLACE(REPLACE([value], ' ', ''), ',', '.') AS float) AS [value]
                FROM #tmp_ge_sales
                WHERE materialge IS NOT NULL AND store_no IS NOT NULL
            ) AS A
            LEFT JOIN dbo.GE_PIVOT_SKU AS B ON B.material = A.materialge
            LEFT JOIN dbo.GE_PIVOT_Stores AS C ON C.store_ge = A.store_no
            GROUP BY B.id, C.id, YEAR(A.[date]), MONTH(A.[date]),
                     DATEPART(week, A.[date]), DAY(A.[date])
        ) AS TMP
            ON BASE.date_year = TMP.date_year AND BASE.date_month = TMP.date_month
           AND BASE.date_week = TMP.date_week AND BASE.date_day = TMP.date_day
           AND BASE.ge_pivot_sku_id = TMP.ge_pivot_sku_id
           AND BASE.ge_pivot_store_id = TMP.ge_pivot_store_id
        WHEN MATCHED THEN
            UPDATE SET sales = TMP.sales, [value] = TMP.[value]
        WHEN NOT MATCHED THEN
            INSERT (ge_pivot_sku_id, ge_pivot_store_id, date_year, date_month, date_week, date_day, sales, [value])
            VALUES (TMP.ge_pivot_sku_id, TMP.ge_pivot_store_id, TMP.date_year, TMP.date_month,
                    TMP.date_week, TMP.date_day, TMP.sales, TMP.[value])
        OUTPUT inserted.ge_pivot_sku_id, DATEFROMPARTS(inserted.date_year, inserted.date_month, 1)
            INTO @loaded (sku_id, period);

        -- Повторная выгрузка заменяет список за месяц, архивная сохраняет более свежий список.
        DECLARE @period date = (SELECT MAX(period) FROM @loaded);
        IF @period IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM dbo.GE_PIVOT_SKU WHERE last_sales_period > @period
        )
        BEGIN
            UPDATE P
            SET last_sales_period = F.period
            FROM dbo.GE_PIVOT_SKU AS P
            LEFT JOIN (
                SELECT DISTINCT sku_id, period FROM @loaded WHERE period = @period
            ) AS F ON F.sku_id = P.id
            WHERE P.last_sales_period = @period OR F.sku_id IS NOT NULL;
        END;

        IF @own_transaction = 1 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @own_transaction = 1 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

ALTER PROCEDURE [dbo].[GE_PROC_MERGE_Stock] (@path nvarchar(100))
AS
BEGIN
    SET XACT_ABORT ON;

    DECLARE @sql nvarchar(500);
    CREATE TABLE #tmp_ge_stock (
        eng nvarchar(250),
        materialge nvarchar(250) COLLATE DATABASE_DEFAULT,
        store_no nvarchar(250) COLLATE DATABASE_DEFAULT,
        stock nvarchar(250),
        [date] nvarchar(250)
    );

    SET @sql = N'BULK INSERT #tmp_ge_stock FROM '''
             + REPLACE(@path, N'''', N'''''')
             + N''' WITH (CODEPAGE = ''65001'', FIRSTROW = 2,
                          FIELDTERMINATOR = '';'', ROWTERMINATOR = ''\n'')';
    EXEC(@sql);

    DELETE FROM #tmp_ge_stock
    WHERE materialge IS NULL;

    DECLARE @own_transaction bit = CASE WHEN @@TRANCOUNT = 0 THEN 1 ELSE 0 END;
    BEGIN TRY
        IF @own_transaction = 1 BEGIN TRANSACTION;

        -- Продажи и остатки могут одновременно пополнять одни и те же позиции.
        MERGE dbo.GE_PIVOT_SKU WITH (TABLOCKX) AS BASE
        USING (SELECT DISTINCT materialge FROM #tmp_ge_stock) AS TMP
            ON BASE.material = TMP.materialge
        WHEN NOT MATCHED THEN
            INSERT (material) VALUES (TMP.materialge);

        MERGE dbo.GE_PIVOT_Stores AS BASE
        USING (SELECT DISTINCT store_no FROM #tmp_ge_stock) AS TMP
            ON BASE.store_ge = TMP.store_no
        WHEN NOT MATCHED THEN
            INSERT (store_ge) VALUES (TMP.store_no);

        DECLARE @loaded TABLE (sku_id int, period date);

        MERGE dbo.GE_DATA_Stock AS BASE
        USING (
            SELECT B.id AS ge_pivot_sku_id, C.id AS ge_pivot_store_id,
                   YEAR(A.[date]) AS date_year, MONTH(A.[date]) AS date_month,
                   DATEPART(week, A.[date]) AS date_week, DAY(A.[date]) AS date_day,
                   SUM(A.stock) AS stock
            FROM (
                SELECT TRY_PARSE(REPLACE([date], '''', '') AS date USING 'de-DE') AS [date],
                       materialge, store_no,
                       CAST(REPLACE(REPLACE(stock, ' ', ''), ',', '.') AS real) AS stock
                FROM #tmp_ge_stock
                WHERE materialge IS NOT NULL AND store_no IS NOT NULL
            ) AS A
            LEFT JOIN dbo.GE_PIVOT_SKU AS B ON B.material = A.materialge
            LEFT JOIN dbo.GE_PIVOT_Stores AS C ON C.store_ge = A.store_no
            GROUP BY B.id, C.id, YEAR(A.[date]), MONTH(A.[date]),
                     DATEPART(week, A.[date]), DAY(A.[date])
        ) AS TMP
            ON BASE.date_year = TMP.date_year AND BASE.date_month = TMP.date_month
           AND BASE.date_week = TMP.date_week AND BASE.date_day = TMP.date_day
           AND BASE.ge_pivot_sku_id = TMP.ge_pivot_sku_id
           AND BASE.ge_pivot_store_id = TMP.ge_pivot_store_id
        WHEN MATCHED THEN
            UPDATE SET stock = TMP.stock
        WHEN NOT MATCHED THEN
            INSERT (ge_pivot_sku_id, ge_pivot_store_id, date_year, date_month, date_week, date_day, stock)
            VALUES (TMP.ge_pivot_sku_id, TMP.ge_pivot_store_id, TMP.date_year, TMP.date_month,
                    TMP.date_week, TMP.date_day, TMP.stock)
        OUTPUT inserted.ge_pivot_sku_id, DATEFROMPARTS(inserted.date_year, inserted.date_month, 1)
            INTO @loaded (sku_id, period);

        -- Повторная выгрузка заменяет список за месяц, архивная сохраняет более свежий список.
        DECLARE @period date = (SELECT MAX(period) FROM @loaded);
        IF @period IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM dbo.GE_PIVOT_SKU WHERE last_stock_period > @period
        )
        BEGIN
            UPDATE P
            SET last_stock_period = F.period
            FROM dbo.GE_PIVOT_SKU AS P
            LEFT JOIN (
                SELECT DISTINCT sku_id, period FROM @loaded WHERE period = @period
            ) AS F ON F.sku_id = P.id
            WHERE P.last_stock_period = @period OR F.sku_id IS NOT NULL;
        END;

        IF @own_transaction = 1 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @own_transaction = 1 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
