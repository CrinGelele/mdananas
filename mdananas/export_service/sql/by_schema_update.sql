-- Изменения структуры BY. На уже обновлённой IDEAL повторно выполнять не нужно.
-- Продажи и [15_BY].[BY_TMP_Sales] не изменяются.
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH(N'[15_BY].[BY_PIVOT_SKU]', N'by_competitor_sku_id') IS NULL
        EXEC(N'ALTER TABLE [15_BY].[BY_PIVOT_SKU] ADD by_competitor_sku_id int NULL');

    IF COL_LENGTH(N'[15_BY].[BY_REF_Competitors_SKU]', N'by_pivot_sku_id') IS NOT NULL
    BEGIN
        EXEC sys.sp_executesql N'
            IF EXISTS (
                SELECT c.id
                FROM [15_BY].[BY_REF_Competitors_SKU] c
                LEFT JOIN [15_BY].[BY_PIVOT_SKU] p ON p.id = c.by_pivot_sku_id
                WHERE c.by_pivot_sku_id IS NOT NULL AND p.id IS NULL
            )
                THROW 51101, N''Есть ссылки конкурентов на несуществующие SKU.'', 1;

            IF EXISTS (
                SELECT c.by_pivot_sku_id
                FROM [15_BY].[BY_REF_Competitors_SKU] c
                WHERE c.by_pivot_sku_id IS NOT NULL
                GROUP BY c.by_pivot_sku_id
                HAVING COUNT(*) > 1
            )
                THROW 51102, N''Одному SKU соответствуют несколько конкурентов.'', 1;

            IF EXISTS (
                SELECT 1
                FROM [15_BY].[BY_REF_Competitors_SKU] c
                JOIN [15_BY].[BY_PIVOT_SKU] p ON p.id = c.by_pivot_sku_id
                WHERE p.by_competitor_sku_id IS NOT NULL
                  AND p.by_competitor_sku_id <> c.id
            )
                THROW 51103, N''Связи с конкурентами уже отличаются: требуется ручная проверка.'', 1;

            UPDATE p
            SET by_competitor_sku_id = c.id
            FROM [15_BY].[BY_PIVOT_SKU] p
            JOIN [15_BY].[BY_REF_Competitors_SKU] c ON c.by_pivot_sku_id = p.id
            WHERE p.by_competitor_sku_id IS NULL;
        ';

        DECLARE @constraint sysname;

        SELECT TOP (1) @constraint = fk.name
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id
        WHERE fk.parent_object_id = OBJECT_ID(N'[15_BY].[BY_REF_Competitors_SKU]')
          AND c.name = N'by_pivot_sku_id';

        IF @constraint IS NOT NULL
            EXEC(N'ALTER TABLE [15_BY].[BY_REF_Competitors_SKU] DROP CONSTRAINT ' + QUOTENAME(@constraint));

        SET @constraint = NULL;
        SELECT TOP (1) @constraint = kc.name
        FROM sys.key_constraints kc
        JOIN sys.index_columns ic ON ic.object_id = kc.parent_object_id AND ic.index_id = kc.unique_index_id
        JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
        WHERE kc.parent_object_id = OBJECT_ID(N'[15_BY].[BY_REF_Competitors_SKU]')
          AND kc.type = 'UQ'
          AND c.name = N'by_pivot_sku_id';

        IF @constraint IS NOT NULL
            EXEC(N'ALTER TABLE [15_BY].[BY_REF_Competitors_SKU] DROP CONSTRAINT ' + QUOTENAME(@constraint));

        EXEC(N'ALTER TABLE [15_BY].[BY_REF_Competitors_SKU] DROP COLUMN by_pivot_sku_id');
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.foreign_key_columns fkc
        WHERE fkc.parent_object_id = OBJECT_ID(N'[15_BY].[BY_PIVOT_SKU]')
          AND fkc.referenced_object_id = OBJECT_ID(N'[15_BY].[BY_REF_Competitors_SKU]')
          AND COL_NAME(fkc.parent_object_id, fkc.parent_column_id) = N'by_competitor_sku_id'
          AND COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) = N'id'
    )
        EXEC(N'ALTER TABLE [15_BY].[BY_PIVOT_SKU] WITH CHECK
            ADD CONSTRAINT FK_BY_PIVOT_SKU_BY_REF_Competitors_SKU
            FOREIGN KEY (by_competitor_sku_id)
            REFERENCES [15_BY].[BY_REF_Competitors_SKU](id)');

    IF COL_LENGTH(N'[15_BY].[BY_PIVOT_SKU]', N'is_last_upload') IS NULL
        ALTER TABLE [15_BY].[BY_PIVOT_SKU]
        ADD is_last_upload bit NOT NULL
            CONSTRAINT DF_BY_PIVOT_SKU_is_last_upload DEFAULT (0);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
