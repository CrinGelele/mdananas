SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE [17_KASPI].[KASPI_PROC_MERGE_Sales]
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET ANSI_PADDING ON;
    SET ANSI_WARNINGS ON;
    SET ARITHABORT ON;
    SET CONCAT_NULL_YIELDS_NULL ON;
    SET NUMERIC_ROUNDABORT OFF;

    BEGIN TRY
        BEGIN TRANSACTION;

        MERGE [17_KASPI].[KASPI_PIVOT_SKU] AS BASE
        USING (
            SELECT source_key COLLATE Latin1_General_100_BIN2 AS source_key,
                   material COLLATE Latin1_General_100_BIN2 AS material,
                   MIN(material_desc_kaspi) AS material_desc_kaspi,
                   MIN(material_desc_own) AS material_desc_own
            FROM [17_KASPI].[KASPI_TMP_Sales]
            GROUP BY source_key COLLATE Latin1_General_100_BIN2,
                     material COLLATE Latin1_General_100_BIN2
        ) AS TMP
            ON BASE.[source_key] = TMP.[source_key]
            AND BASE.[material] = TMP.[material]
        WHEN MATCHED THEN UPDATE SET
            BASE.[material_desc_kaspi] = TMP.[material_desc_kaspi],
            BASE.[material_desc_own] = TMP.[material_desc_own],
            BASE.updated_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT (
            [source_key], [material], [material_desc_kaspi], [material_desc_own]
        ) VALUES (
            TMP.[source_key], TMP.[material], TMP.[material_desc_kaspi], TMP.[material_desc_own]
        );

        MERGE [17_KASPI].[KASPI_DATA_Orders] AS BASE
        USING (
            SELECT DISTINCT
                [source_key] COLLATE Latin1_General_100_BIN2 AS [source_key],
                [order_number] COLLATE Latin1_General_100_BIN2 AS [order_number],
                CONVERT(datetime2(0), [receive_dt], 126) AS [receive_dt],
                [receive_has_time], [change_dt], [plan_dt], CONVERT(datetime2(0), [fact_dt], 126) AS [fact_dt],
                [fact_has_time], [address], [status], [cancellation_reason], [payment_method],
                [shipment_method], [courier_service], [shipment_warehouse], [signature_required], [currency],
                [ship_price_cust], [ship_price_store], [ship_compensation]
            FROM [17_KASPI].[KASPI_TMP_Sales]
        ) AS TMP
            ON BASE.[source_key] = TMP.[source_key]
            AND BASE.[order_number] = TMP.[order_number]
        WHEN MATCHED THEN UPDATE SET
            BASE.[receive_dt] = TMP.[receive_dt],
            BASE.[receive_has_time] = TMP.[receive_has_time],
            BASE.[change_dt] = TMP.[change_dt],
            BASE.[plan_dt] = TMP.[plan_dt],
            BASE.[fact_dt] = TMP.[fact_dt],
            BASE.[fact_has_time] = TMP.[fact_has_time],
            BASE.[address] = TMP.[address],
            BASE.[status] = TMP.[status],
            BASE.[cancellation_reason] = TMP.[cancellation_reason],
            BASE.[payment_method] = TMP.[payment_method],
            BASE.[shipment_method] = TMP.[shipment_method],
            BASE.[courier_service] = TMP.[courier_service],
            BASE.[shipment_warehouse] = TMP.[shipment_warehouse],
            BASE.[signature_required] = TMP.[signature_required],
            BASE.[currency] = TMP.[currency],
            BASE.[ship_price_cust] = TMP.[ship_price_cust],
            BASE.[ship_price_store] = TMP.[ship_price_store],
            BASE.[ship_compensation] = TMP.[ship_compensation],
            BASE.updated_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT (
            [source_key], [order_number], [receive_dt], [receive_has_time], [change_dt], [plan_dt], [fact_dt],
            [fact_has_time], [address], [status], [cancellation_reason], [payment_method], [shipment_method],
            [courier_service], [shipment_warehouse], [signature_required], [currency], [ship_price_cust],
            [ship_price_store], [ship_compensation]
        ) VALUES (
            TMP.[source_key], TMP.[order_number], TMP.[receive_dt], TMP.[receive_has_time], TMP.[change_dt],
            TMP.[plan_dt], TMP.[fact_dt], TMP.[fact_has_time], TMP.[address], TMP.[status],
            TMP.[cancellation_reason], TMP.[payment_method], TMP.[shipment_method], TMP.[courier_service],
            TMP.[shipment_warehouse], TMP.[signature_required], TMP.[currency], TMP.[ship_price_cust],
            TMP.[ship_price_store], TMP.[ship_compensation]
        );

        MERGE [17_KASPI].[KASPI_DATA_Order_Lines] AS BASE
        USING (
            SELECT T.source_key COLLATE Latin1_General_100_BIN2 AS source_key,
                   O.id AS kaspi_order_id, P.id AS kaspi_pivot_sku_id,
                   T.[material_desc_kaspi], T.[material_desc_own], T.[category], T.[volume], T.[value]
            FROM [17_KASPI].[KASPI_TMP_Sales] T
            JOIN [17_KASPI].[KASPI_DATA_Orders] O
                ON O.source_key = T.source_key COLLATE Latin1_General_100_BIN2
                   AND O.order_number = T.order_number COLLATE Latin1_General_100_BIN2
            JOIN [17_KASPI].[KASPI_PIVOT_SKU] P
                ON P.source_key = T.source_key COLLATE Latin1_General_100_BIN2
                   AND P.material = T.material COLLATE Latin1_General_100_BIN2
        ) AS TMP
            ON BASE.[source_key] = TMP.[source_key]
            AND BASE.[kaspi_order_id] = TMP.[kaspi_order_id]
            AND BASE.[kaspi_pivot_sku_id] = TMP.[kaspi_pivot_sku_id]
        WHEN MATCHED THEN UPDATE SET
            BASE.[material_desc_kaspi] = TMP.[material_desc_kaspi],
            BASE.[material_desc_own] = TMP.[material_desc_own],
            BASE.[category] = TMP.[category],
            BASE.[volume] = TMP.[volume],
            BASE.[value] = TMP.[value],
            BASE.updated_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT (
            [source_key], [kaspi_order_id], [kaspi_pivot_sku_id], [material_desc_kaspi], [material_desc_own],
            [category], [volume], [value]
        ) VALUES (
            TMP.[source_key], TMP.[kaspi_order_id], TMP.[kaspi_pivot_sku_id], TMP.[material_desc_kaspi],
            TMP.[material_desc_own], TMP.[category], TMP.[volume], TMP.[value]
        );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
