-- Связь товаров конкурентов Грузии с общим справочником ROOT.
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH(N'dbo.GE_PIVOT_Competing_skus', N'root_cmp_id') IS NULL
        EXEC(N'ALTER TABLE dbo.GE_PIVOT_Competing_skus ADD root_cmp_id int NULL');

    DECLARE @fk sysname, @needs_check bit;
    SELECT TOP (1) @fk = f.name,
           @needs_check = CASE WHEN f.is_disabled = 1 OR f.is_not_trusted = 1 THEN 1 ELSE 0 END
    FROM sys.foreign_key_columns AS c
    JOIN sys.foreign_keys AS f ON f.object_id = c.constraint_object_id
    WHERE c.parent_object_id = OBJECT_ID(N'dbo.GE_PIVOT_Competing_skus')
      AND COL_NAME(c.parent_object_id, c.parent_column_id) = N'root_cmp_id'
      AND c.referenced_object_id = OBJECT_ID(N'[00_ROOT].[ROOT_REF_SKU_CMP]')
      AND COL_NAME(c.referenced_object_id, c.referenced_column_id) = N'id'
    ORDER BY f.is_disabled, f.is_not_trusted;

    IF @fk IS NULL
        EXEC(N'ALTER TABLE dbo.GE_PIVOT_Competing_skus WITH CHECK
               ADD CONSTRAINT FK_GE_PIVOT_Competing_skus_ROOT_REF_SKU_CMP
               FOREIGN KEY (root_cmp_id) REFERENCES [00_ROOT].[ROOT_REF_SKU_CMP](id)');
    ELSE IF @needs_check = 1
    BEGIN
        DECLARE @sql nvarchar(512) = N'ALTER TABLE dbo.GE_PIVOT_Competing_skus WITH CHECK CHECK CONSTRAINT '
                                     + QUOTENAME(@fk);
        EXEC sys.sp_executesql @sql;
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
