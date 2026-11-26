SET XACT_ABORT ON;
DECLARE @ApplySchema bit = 0;  -- Создание связи с CU
DECLARE @ApplyExact bit = 0;   -- Запись точных совпадений

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @fk sysname, @fk_ready bit;
    SELECT TOP (1) @fk = f.name,
           @fk_ready = CASE WHEN f.is_disabled = 0 AND f.is_not_trusted = 0 THEN 1 ELSE 0 END
    FROM sys.foreign_key_columns AS k
    JOIN sys.foreign_keys AS f ON f.object_id = k.constraint_object_id
    WHERE k.parent_object_id = OBJECT_ID(N'dbo.GE_PIVOT_SKU')
      AND COL_NAME(k.parent_object_id, k.parent_column_id) = N'root_cu_id'
      AND k.referenced_object_id = OBJECT_ID(N'[00_ROOT].[ROOT_REF_SKU_CU]')
      AND COL_NAME(k.referenced_object_id, k.referenced_column_id) = N'id'
    ORDER BY f.is_disabled, f.is_not_trusted;

    IF @ApplySchema = 1
    BEGIN
        IF COL_LENGTH(N'dbo.GE_PIVOT_SKU', N'root_cu_id') IS NULL
            EXEC(N'ALTER TABLE dbo.GE_PIVOT_SKU ADD root_cu_id int NULL');

        IF @fk IS NULL
            EXEC(N'ALTER TABLE dbo.GE_PIVOT_SKU WITH CHECK
                   ADD CONSTRAINT FK_GE_PIVOT_SKU_ROOT_REF_SKU_CU
                   FOREIGN KEY (root_cu_id) REFERENCES [00_ROOT].[ROOT_REF_SKU_CU](id)');
        ELSE IF @fk_ready = 0
        BEGIN
            DECLARE @check_fk nvarchar(512) = N'ALTER TABLE dbo.GE_PIVOT_SKU WITH CHECK CHECK CONSTRAINT '
                                               + QUOTENAME(@fk);
            EXEC sys.sp_executesql @check_fk;
        END;
    END
    ELSE IF @ApplyExact = 1 AND ISNULL(@fk_ready, 0) = 0
        THROW 51120, N'Сначала создайте или включите связь с CU с помощью @ApplySchema.', 1;

    -- Артикулы CU и TU могут указывать на один товар.
    DROP TABLE IF EXISTS #ge_cu_matches;
    ;WITH catalog AS (
        SELECT LTRIM(RTRIM(xcode_cu)) COLLATE Latin1_General_100_BIN2 AS xcode, id AS cu_id
        FROM [00_ROOT].[ROOT_REF_SKU_CU]
        UNION
        SELECT LTRIM(RTRIM(xcode_tu)) COLLATE Latin1_General_100_BIN2, root_cu_id
        FROM [00_ROOT].[ROOT_REF_SKU_TU]
        WHERE root_cu_id IS NOT NULL
    )
    SELECT p.id AS pivot_id, p.material, p.ge_sku_id, r.id AS old_root_id,
           r.xcode AS old_xcode, r.sku AS old_name,
           COUNT(c.cu_id) AS candidates,
           CASE WHEN COUNT(c.cu_id) = 1 THEN MIN(c.cu_id) END AS candidate_cu_id,
           CAST(NULL AS int) AS current_cu_id, CAST(NULL AS nvarchar(40)) AS match_status
    INTO #ge_cu_matches
    FROM dbo.GE_PIVOT_SKU AS p
    LEFT JOIN dbo.GE_REF_SKU AS g ON g.id = p.ge_sku_id
    LEFT JOIN dbo.ROOT_REF_SKU AS r ON r.id = g.root_sku_id
    LEFT JOIN catalog AS c
        ON c.xcode = NULLIF(LTRIM(RTRIM(r.xcode)), '') COLLATE Latin1_General_100_BIN2
    GROUP BY p.id, p.material, p.ge_sku_id, r.id, r.xcode, r.sku;

    IF COL_LENGTH(N'dbo.GE_PIVOT_SKU', N'root_cu_id') IS NOT NULL
        EXEC(N'UPDATE m SET current_cu_id = p.root_cu_id
               FROM #ge_cu_matches AS m JOIN dbo.GE_PIVOT_SKU AS p ON p.id = m.pivot_id');

    UPDATE m SET match_status = CASE
        WHEN m.current_cu_id IS NOT NULL THEN N'Уже привязано'
        WHEN m.ge_sku_id IS NULL THEN N'Без грузинской привязки'
        WHEN m.candidates = 0 THEN N'Нет точного совпадения'
        WHEN m.candidates > 1 THEN N'Несколько CU'
        WHEN EXISTS (SELECT 1 FROM #ge_cu_matches AS other
                     WHERE other.ge_sku_id = m.ge_sku_id
                       AND other.current_cu_id <> m.candidate_cu_id)
            THEN N'У карточки указан другой CU'
        ELSE N'Одно точное совпадение'
    END
    FROM #ge_cu_matches AS m;

    SELECT match_status, COUNT(*) AS positions
    FROM #ge_cu_matches
    GROUP BY match_status
    ORDER BY match_status;

    SELECT m.pivot_id, m.material, m.old_xcode, m.old_name, m.current_cu_id,
           m.candidate_cu_id, cu.xcode_cu, d.rus_definition, m.match_status
    FROM #ge_cu_matches AS m
    LEFT JOIN [00_ROOT].[ROOT_REF_SKU_CU] AS cu ON cu.id = m.candidate_cu_id
    LEFT JOIN [00_ROOT].[ROOT_REF_SKU_Definitions] AS d ON d.id = cu.root_pd_id
    ORDER BY m.match_status, m.old_xcode, m.pivot_id;

    IF @ApplyExact = 1
        EXEC(N'UPDATE p SET root_cu_id = m.candidate_cu_id
               FROM dbo.GE_PIVOT_SKU AS p
               JOIN #ge_cu_matches AS m ON m.pivot_id = p.id AND m.ge_sku_id = p.ge_sku_id
               JOIN dbo.GE_REF_SKU AS g ON g.id = p.ge_sku_id AND g.root_sku_id = m.old_root_id
               WHERE m.match_status = N''Одно точное совпадение'' AND p.root_cu_id IS NULL
                 AND NOT EXISTS (SELECT 1 FROM dbo.GE_PIVOT_SKU AS sibling
                                 WHERE sibling.ge_sku_id = p.ge_sku_id
                                   AND sibling.root_cu_id <> m.candidate_cu_id);
               SELECT @@ROWCOUNT AS filled_positions;');

    DROP TABLE #ge_cu_matches;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
