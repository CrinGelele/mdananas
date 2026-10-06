import os
from django.apps import AppConfig


class DatapullServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'datapull_service'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            from datapull_service.tasks import scheduler
            try:
                scheduler.start()
            except KeyboardInterrupt:
                scheduler.shutdown()
