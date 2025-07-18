from django.db import connections
from mdananas.idealSchemaEditor import IdealSchemaEditor
import tempfile
import csv
import os

def bulk_insert_to_sqlserver(csv_path, model):
    with connections['ideal'].cursor() as cursor:
        cursor.execute(f"""
            BULK INSERT {model._meta.db_table}
            FROM '{csv_path}'
            WITH (
                CODEPAGE = '65001',
                FIRSTROW = 2,
                ROWTERMINATOR = '\r\n',
                FIELDTERMINATOR = ';'
            )
        """)
    if os.path.exists(csv_path):
        os.remove(csv_path)

def upload_file(file_data, model, proc, big=False):
    with connections['ideal'].cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {model._meta.db_table}")
        with IdealSchemaEditor(connection=connections['ideal']) as schema_editor:
            schema_editor.create_model(model)
            if big:
                NETWORK_FOLDER = r"\\hru03\Public\BI\40. ERP data for SQL"
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', encoding='utf-8', dir=NETWORK_FOLDER, delete=False) as tmp_file:
                    writer = csv.writer(tmp_file, delimiter=';', lineterminator='\n')
                    writer.writerow([f.name for f in model._meta.fields])
                    for obj in file_data:
                        writer.writerow([getattr(obj, f.name) for f in model._meta.fields])
                    tmp_file.flush()
                bulk_insert_to_sqlserver(tmp_file.name.replace(os.sep, '/'), model)
            else:
                model.objects.bulk_create(file_data)
            cursor.execute(f"EXEC {proc}")
            cursor.execute(f"DROP TABLE IF EXISTS {model._meta.db_table}")