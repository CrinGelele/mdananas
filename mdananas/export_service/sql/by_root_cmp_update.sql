-- Связь SKU Беларуси с общим справочником конкурентов ROOT.
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH(N'[15_BY].[BY_PIVOT_SKU]', N'root_cmp_id') IS NULL
        EXEC(N'ALTER TABLE [15_BY].[BY_PIVOT_SKU] ADD root_cmp_id int NULL');

    IF NOT EXISTS (
        SELECT 1
        FROM sys.foreign_key_columns fkc
        WHERE fkc.parent_object_id = OBJECT_ID(N'[15_BY].[BY_PIVOT_SKU]')
          AND fkc.referenced_object_id = OBJECT_ID(N'[00_ROOT].[ROOT_REF_SKU_CMP]')
          AND COL_NAME(fkc.parent_object_id, fkc.parent_column_id) = N'root_cmp_id'
          AND COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) = N'id'
    )
        EXEC(N'ALTER TABLE [15_BY].[BY_PIVOT_SKU] WITH CHECK
            ADD CONSTRAINT FK_BY_PIVOT_SKU_ROOT_REF_SKU_CMP
            FOREIGN KEY (root_cmp_id)
            REFERENCES [00_ROOT].[ROOT_REF_SKU_CMP](id)');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
