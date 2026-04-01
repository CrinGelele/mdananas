from django.apps import AppConfig


class RootServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'root_service'

    def ready(self):
        # Импортируем сигналы при запуске приложения
        import root_service.signals.ref_sku_signals  # замените your_app на имя вашего приложения