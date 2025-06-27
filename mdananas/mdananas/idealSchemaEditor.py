from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db import connections

class IdealSchemaEditor(BaseDatabaseSchemaEditor):
    def __init__(self, *args, **kwargs):
        kwargs['connection'] = connections['ideal']  # Принудительно подключаемся
        super().__init__(*args, **kwargs)