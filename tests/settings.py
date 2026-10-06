from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "mdananas"
SECRET_KEY = "local-tests-only"
INSTALLED_APPS = ["root_service", "datapull_service"]
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
    "ideal": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
}
ROOT_URLCONF = "tests.urls"
DATABASE_ROUTERS = []
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
PRICEM_RETRY_DELAYS = (60, 300, 900)
PRICEM_POLL_SECONDS = 15
PRICEVA_EXPORT_URL = "https://example.invalid/export?f=test-only"
