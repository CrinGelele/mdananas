from django.core.management.base import BaseCommand, CommandError

from datapull_service.pricem.errors import safe_error
from datapull_service.pricem.locking import import_lock
from datapull_service.pricem.schema import prepare_schema


class Command(BaseCommand):
    help = "Prepare Priceva run tracking, external IDs and scheduled time (SQL Server)."
    requires_system_checks = []

    def handle(self, *args, **options):
        try:
            with import_lock() as acquired:
                if not acquired:
                    raise CommandError(
                        "Another Priceva importer is running; stop it before preparing the schema"
                    )
                prepare_schema()
        except Exception as error:
            raise CommandError(safe_error(error)) from None
        self.stdout.write(
            self.style.SUCCESS(
                "Priceva schema prepared; historical hour values retained in upload_time_legacy_hour"
            )
        )
