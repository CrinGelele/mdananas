-- Run on the IDEAL connection. Application timestamps are stored in UTC;
-- upload_date/upload_time describe the scheduled occurrence in Moscow.
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF DB_NAME() <> N'IDEAL'
        THROW 51000, 'Priceva preparation must run on the IDEAL database.', 1;
    IF OBJECT_ID(N'[03_PRICEM].[PRICEM_DATA_Source_Offers]', N'U') IS NULL
        THROW 51000, 'Existing Priceva tables were not found.', 1;

    DECLARE @offers int = OBJECT_ID(N'[03_PRICEM].[PRICEM_DATA_Source_Offers]');
    DECLARE @column int = COLUMNPROPERTY(@offers, N'upload_time', 'ColumnId');
    DECLARE @type nvarchar(128) = (
        SELECT TYPE_NAME(system_type_id) FROM sys.columns
        WHERE object_id = @offers AND name = N'upload_time'
    );
    IF @type IN (N'int', N'smallint', N'tinyint', N'bigint')
    BEGIN
        EXEC sys.sp_executesql N'IF EXISTS (SELECT 1 FROM [03_PRICEM].[PRICEM_DATA_Source_Offers]
                   WHERE upload_time IS NULL OR upload_time < 0 OR upload_time > 23)
            THROW 51000, ''Historical upload_time must contain hours 0..23. Reconcile invalid rows first.'', 1;';
        IF COL_LENGTH(N'[03_PRICEM].[PRICEM_DATA_Source_Offers]', N'upload_time_legacy_hour') IS NOT NULL
            THROW 51000, 'A legacy upload_time backup already exists; inspect the schema before proceeding.', 1;
        IF EXISTS (SELECT 1 FROM sys.index_columns WHERE object_id = @offers AND column_id = @column)
           OR EXISTS (SELECT 1 FROM sys.default_constraints WHERE parent_object_id = @offers AND parent_column_id = @column)
           OR EXISTS (SELECT 1 FROM sys.sql_expression_dependencies WHERE referenced_id = @offers AND referenced_minor_id = @column)
           OR EXISTS (SELECT 1 FROM sys.foreign_key_columns WHERE
                      (parent_object_id = @offers AND parent_column_id = @column)
                      OR (referenced_object_id = @offers AND referenced_column_id = @column))
            THROW 51000, 'upload_time has SQL dependencies. Adapt them before converting the column.', 1;

        EXEC sys.sp_rename N'[03_PRICEM].[PRICEM_DATA_Source_Offers].[upload_time]', N'upload_time_legacy_hour', N'COLUMN';
        DECLARE @alter nvarchar(max) = N'ALTER TABLE [03_PRICEM].[PRICEM_DATA_Source_Offers] ALTER COLUMN upload_time_legacy_hour ' + @type + N' NULL';
        EXEC sys.sp_executesql @alter;
        EXEC sys.sp_executesql N'ALTER TABLE [03_PRICEM].[PRICEM_DATA_Source_Offers] ADD upload_time time(0) NULL';
        EXEC sys.sp_executesql N'UPDATE [03_PRICEM].[PRICEM_DATA_Source_Offers]
                                SET upload_time = TIMEFROMPARTS(upload_time_legacy_hour, 0, 0, 0, 0)';
        EXEC sys.sp_executesql N'ALTER TABLE [03_PRICEM].[PRICEM_DATA_Source_Offers] ALTER COLUMN upload_time time(0) NOT NULL';
    END
    ELSE IF @type IS NULL OR @type <> N'time'
        THROW 51000, 'Unsupported upload_time type; expected integer hours or SQL time.', 1;

    IF COL_LENGTH(N'[03_PRICEM].[PRICEM_DATA_INT_Monitoring]', N'priceva_product_id') IS NULL
        ALTER TABLE [03_PRICEM].[PRICEM_DATA_INT_Monitoring] ADD priceva_product_id nvarchar(100) COLLATE Latin1_General_100_BIN2 NULL;
    IF COL_LENGTH(N'[03_PRICEM].[PRICEM_DATA_EXT_Monitoring]', N'priceva_product_id') IS NULL
        ALTER TABLE [03_PRICEM].[PRICEM_DATA_EXT_Monitoring] ADD priceva_product_id nvarchar(100) COLLATE Latin1_General_100_BIN2 NULL;
    IF COL_LENGTH(N'[03_PRICEM].[PRICEM_DATA_Monitoring_Sources]', N'priceva_source_id') IS NULL
        ALTER TABLE [03_PRICEM].[PRICEM_DATA_Monitoring_Sources] ADD priceva_source_id nvarchar(100) COLLATE Latin1_General_100_BIN2 NULL;

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'[03_PRICEM].[PRICEM_DATA_INT_Monitoring]') AND name = N'UX_PRICEM_INT_PricevaID')
        EXEC sys.sp_executesql N'CREATE UNIQUE INDEX UX_PRICEM_INT_PricevaID ON [03_PRICEM].[PRICEM_DATA_INT_Monitoring](priceva_product_id) WHERE priceva_product_id IS NOT NULL';
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'[03_PRICEM].[PRICEM_DATA_EXT_Monitoring]') AND name = N'UX_PRICEM_EXT_PricevaID')
        EXEC sys.sp_executesql N'CREATE UNIQUE INDEX UX_PRICEM_EXT_PricevaID ON [03_PRICEM].[PRICEM_DATA_EXT_Monitoring](priceva_product_id) WHERE priceva_product_id IS NOT NULL';
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'[03_PRICEM].[PRICEM_DATA_Monitoring_Sources]') AND name = N'UX_PRICEM_Source_PricevaID')
        EXEC sys.sp_executesql N'CREATE UNIQUE INDEX UX_PRICEM_Source_PricevaID ON [03_PRICEM].[PRICEM_DATA_Monitoring_Sources](priceva_source_id) WHERE priceva_source_id IS NOT NULL';

    IF OBJECT_ID(N'[MDANANAS].[dbo].[DATAPULL_PRICEM_RUNS]', N'U') IS NULL
    BEGIN
        CREATE TABLE [MDANANAS].[dbo].[DATAPULL_PRICEM_RUNS] (
            id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
            schedule_id bigint NOT NULL,
            scheduled_at datetime2(0) NOT NULL,
            next_at datetime2(0) NOT NULL,
            status nvarchar(16) NOT NULL DEFAULT N'pending',
            attempts int NOT NULL DEFAULT 0,
            started_at datetime2(6) NULL,
            finished_at datetime2(6) NULL,
            next_retry_at datetime2(6) NULL,
            fetched_at datetime2(6) NULL,
            payload nvarchar(max) NULL,
            payload_hash nvarchar(64) NOT NULL DEFAULT N'',
            counts nvarchar(max) NOT NULL DEFAULT N'{}',
            last_error nvarchar(max) NOT NULL DEFAULT N'',
            CONSTRAINT UQ_DATAPULL_PRICEM_RunSlot UNIQUE (scheduled_at),
            CONSTRAINT CK_DATAPULL_PRICEM_Status CHECK (status IN (N'pending', N'running', N'retry', N'failed', N'succeeded', N'missed')),
            CONSTRAINT CK_DATAPULL_PRICEM_Attempts CHECK (attempts >= 0)
        );
        CREATE INDEX IX_DATAPULL_PRICEM_Status ON [MDANANAS].[dbo].[DATAPULL_PRICEM_RUNS](status, scheduled_at);
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
