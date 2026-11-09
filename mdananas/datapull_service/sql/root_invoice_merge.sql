-- ROOT Invoice merge based on the production definition supplied 2026-11-09
-- and the applied routing fixes. Compare with OBJECT_DEFINITION before deploy.
-- Requires Lenta recipient mappings to canonical customer ID 59.
CREATE OR ALTER PROCEDURE [00_ROOT].[ROOT_PROC_MERGE_Invoices]
AS
BEGIN
    DECLARE @InsertedCustomers TABLE (erp_name nvarchar(255), id int);
    DECLARE @InsertedTU TABLE (xcode_tu nvarchar(255), id int);
    DECLARE @InsertedMIX TABLE (xcode_mix nvarchar(255), id int);

    MERGE [00_ROOT].ROOT_PIVOT_Customers BASE
    USING (
        SELECT DISTINCT customer,
            CASE
                WHEN customer LIKE N'%ПЕРЕК%СТОК%' THEN shipped_to
                -- The legacy bulk import kept CSV quotes literally. The new
                -- CSV import supplies the unescaped name instead.
                WHEN customer = N'ЛЕНТА ООО'
                     AND shipped_to = N'"ООО ""Лента"", РЦ 7114"'
                    THEN N'ООО "Лента", РЦ 7114'
                WHEN customer = N'ЛЕНТА ООО'
                     AND shipped_to IN (
                         N'ООО "Лента", РЦ 7114',
                         N'Лента РЦ ВАЛИЩЕВО 8133'
                     ) THEN shipped_to
                ELSE customer
            END AS shipped_to
        FROM [00_ROOT].ROOT_TMP_Invoices
    ) TMP ON BASE.erp_name = TMP.customer
         AND BASE.shipped_to = TMP.shipped_to
    WHEN NOT MATCHED THEN INSERT (erp_name, shipped_to)
        VALUES (TMP.customer, TMP.shipped_to)
    OUTPUT TMP.customer, inserted.id INTO @InsertedCustomers;

    INSERT INTO [MDANANAS].[dbo].LOGS_DATAPULL_ROOT
        (date_time, operation_type, operation_details, records_count)
    SELECT SYSDATETIME(), 'PIVOT CUSTOMER INSERT', erp_name, 1
    FROM @InsertedCustomers;

    MERGE [00_ROOT].ROOT_REF_SKU_TU BASE
    USING (
        SELECT DISTINCT TRIM(xcode) xcode
        FROM [00_ROOT].ROOT_TMP_Invoices
        WHERE xcode NOT LIKE N'%MIX%'
    ) TMP ON BASE.xcode_tu = TMP.xcode
    WHEN NOT MATCHED THEN INSERT (xcode_tu) VALUES (TMP.xcode)
    OUTPUT TMP.xcode, inserted.id INTO @InsertedTU;

    INSERT INTO [MDANANAS].[dbo].LOGS_DATAPULL_ROOT
        (date_time, operation_type, operation_details, records_count)
    SELECT SYSDATETIME(), 'TU INSERT', xcode_tu, 1
    FROM @InsertedTU;

    MERGE [00_ROOT].ROOT_REF_SKU_MIX BASE
    USING (
        SELECT DISTINCT TRIM(xcode) xcode
        FROM [00_ROOT].ROOT_TMP_Invoices
        WHERE xcode LIKE N'%MIX%'
    ) TMP ON BASE.xcode_mix = TMP.xcode
    WHEN NOT MATCHED THEN INSERT (xcode_mix) VALUES (TMP.xcode)
    OUTPUT TMP.xcode, inserted.id INTO @InsertedMIX;

    INSERT INTO [MDANANAS].[dbo].LOGS_DATAPULL_ROOT
        (date_time, operation_type, operation_details, records_count)
    SELECT SYSDATETIME(), 'MIX INSERT', xcode_mix, 1
    FROM @InsertedMIX;

    MERGE [00_ROOT].ROOT_DATA_Invoices BASE
    USING (
        SELECT A.date_year, A.date_month, A.date_day,
               B.id root_tu_id, C.id root_mix_id, D.id root_pivot_customer_id,
               A.is_promo,
               SUM(IIF(gsv = 'nan', 0, CAST(gsv AS float))) gsv,
               SUM(IIF(cu = 'nan', 0, CAST(cu AS float))) cu,
               SUM(IIF(gsv = 'nan', 0, CAST(gsv AS float))
                   + IIF([on] = 'nan', 0, CAST([on] AS float))) isv,
               SUM(IIF(contract_conditions = 'nan', 0, CAST(contract_conditions AS float))
                   + IIF(price_increase_delay = 'nan', 0, CAST(price_increase_delay AS float))
                   + IIF(gsv = 'nan', 0, CAST(gsv AS float))) isv_ct,
               SUM(IIF(nsv = 'nan', 0, CAST(nsv AS float))) nsv,
               SUM(IIF(gsv = 'nan', 0, CAST(gsv AS float))
                   + IIF([on] = 'nan', 0, CAST([on] AS float)))
                   + SUM(IIF(contract_conditions_services = 'nan', 0,
                             CAST(contract_conditions_services AS float)))
                   + SUM(IIF(contract_conditions_bonus = 'nan', 0,
                             CAST(contract_conditions_bonus AS float))) nsv_ct
        FROM [00_ROOT].ROOT_TMP_Invoices A
        LEFT JOIN [00_ROOT].ROOT_REF_SKU_TU B ON A.xcode = B.xcode_tu
        LEFT JOIN [00_ROOT].ROOT_REF_SKU_MIX C ON A.xcode = C.xcode_mix
        LEFT JOIN [00_ROOT].ROOT_PIVOT_Customers D
            ON A.customer = D.erp_name
           AND CASE
                WHEN A.customer LIKE N'%ПЕРЕК%СТОК%' THEN A.shipped_to
                WHEN A.customer = N'ЛЕНТА ООО'
                     AND A.shipped_to = N'"ООО ""Лента"", РЦ 7114"'
                    THEN N'ООО "Лента", РЦ 7114'
                WHEN A.customer = N'ЛЕНТА ООО'
                     AND A.shipped_to IN (
                         N'ООО "Лента", РЦ 7114',
                         N'Лента РЦ ВАЛИЩЕВО 8133'
                     ) THEN A.shipped_to
                ELSE A.customer
            END = D.shipped_to
        GROUP BY A.date_year, A.date_month, A.date_day,
                 B.id, C.id, D.id, A.is_promo
    ) TMP ON BASE.date_year = TMP.date_year
         AND BASE.date_month = TMP.date_month
         AND (BASE.date_day = TMP.date_day
              OR (BASE.date_day IS NULL AND TMP.date_day IS NULL))
         AND (BASE.root_tu_id = TMP.root_tu_id
              OR (BASE.root_tu_id IS NULL AND TMP.root_tu_id IS NULL))
         AND (BASE.root_mix_id = TMP.root_mix_id
              OR (BASE.root_mix_id IS NULL AND TMP.root_mix_id IS NULL))
         AND BASE.root_pivot_customer_id = TMP.root_pivot_customer_id
         AND BASE.is_promo = TMP.is_promo
    WHEN MATCHED THEN UPDATE SET
        gsv = TMP.gsv,
        cu = TMP.cu,
        isv = TMP.isv,
        isv_ct = TMP.isv_ct,
        nsv = TMP.nsv,
        nsv_ct = TMP.nsv_ct
    WHEN NOT MATCHED THEN INSERT (
        date_year, date_month, date_day, root_tu_id, root_mix_id,
        root_pivot_customer_id, gsv, cu, isv, isv_ct, nsv, nsv_ct, is_promo
    ) VALUES (
        TMP.date_year, TMP.date_month, TMP.date_day, TMP.root_tu_id, TMP.root_mix_id,
        TMP.root_pivot_customer_id, TMP.gsv, TMP.cu, TMP.isv, TMP.isv_ct,
        TMP.nsv, TMP.nsv_ct, TMP.is_promo
    );

    INSERT INTO [MDANANAS].[dbo].LOGS_DATAPULL_ROOT
        (date_time, operation_type, operation_details, records_count, aggregated_records_count)
    SELECT SYSDATETIME(), 'INVOICE FILE INSERT',
           CONCAT('Prevailing month: ', prevailing_year, '-', prevailing_month),
           total_records, agg_records
    FROM (
        SELECT TOP 1 date_year AS prevailing_year,
                     date_month AS prevailing_month,
                     COUNT(*) AS record_count
        FROM [00_ROOT].ROOT_TMP_Invoices
        GROUP BY date_year, date_month
        ORDER BY COUNT(*) DESC
    ) A
    CROSS JOIN (
        SELECT COUNT(*) AS total_records FROM [00_ROOT].ROOT_TMP_Invoices
    ) B
    CROSS JOIN (
        SELECT COUNT(*) agg_records FROM (
            SELECT date_year, date_month, date_day, xcode, customer
            FROM [00_ROOT].ROOT_TMP_Invoices
            GROUP BY date_year, date_month, date_day, xcode, customer
        ) j
    ) C;
END;
GO
