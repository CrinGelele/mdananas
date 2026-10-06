from pathlib import Path

from django.db import connections

from .errors import ImportConfigurationError


def verify_schema():
    connection = connections["ideal"]
    if connection.vendor != "microsoft":
        raise ImportConfigurationError(
            "Priceva requires SQL Server on the ideal connection"
        )
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT TYPE_NAME(system_type_id) FROM sys.columns
            WHERE object_id = OBJECT_ID(N'[03_PRICEM].[PRICEM_DATA_Source_Offers]')
              AND name = N'upload_time'
        """)
        row = cursor.fetchone()
        if not row or row[0] != "time":
            raise ImportConfigurationError(
                "Prepare the Priceva schema: py manage.py pricem_prepare"
            )
        cursor.execute("""
            SELECT OBJECT_ID(N'[MDANANAS].[dbo].[DATAPULL_PRICEM_RUNS]', N'U'),
                COL_LENGTH(N'[03_PRICEM].[PRICEM_DATA_INT_Monitoring]', N'priceva_product_id'),
                COL_LENGTH(N'[03_PRICEM].[PRICEM_DATA_EXT_Monitoring]', N'priceva_product_id'),
                COL_LENGTH(N'[03_PRICEM].[PRICEM_DATA_Monitoring_Sources]', N'priceva_source_id')
        """)
        if any(value is None for value in cursor.fetchone()):
            raise ImportConfigurationError(
                "Prepare the Priceva schema: py manage.py pricem_prepare"
            )


def prepare_schema():
    connection = connections["ideal"]
    if connection.vendor != "microsoft":
        raise ImportConfigurationError(
            "Schema preparation requires the SQL Server ideal connection"
        )
    path = Path(__file__).resolve().parent.parent / "sql" / "001_pricem_import.sql"
    with connection.cursor() as cursor:
        cursor.execute(path.read_text(encoding="utf-8"))
        while cursor.nextset():
            pass
    verify_schema()
