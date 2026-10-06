from django.core.management.base import BaseCommand, CommandError

from datapull_service.pricem.errors import safe_error
from datapull_service.pricem.runner import run_tick
from datapull_service.pricem.schema import verify_schema


class Command(BaseCommand):
    help = "Run one Priceva scheduling check, or explicitly retry a saved run."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Describe the current slot without API calls or writes",
        )
        parser.add_argument(
            "--retry-run",
            type=int,
            help="Retry this failed run using its saved snapshot",
        )

    def handle(self, *args, **options):
        if options["check"] and options["retry_run"] is not None:
            raise CommandError("--check cannot be combined with --retry-run")
        try:
            verify_schema()
            result = run_tick(
                retry_run_id=options["retry_run"], check_only=options["check"]
            )
        except Exception as error:
            raise CommandError(safe_error(error)) from None
        self.stdout.write(f"{result.status}: {result.message}; run={result.run_id}")
        if result.status in ("retry", "failed", "missed"):
            raise CommandError(
                "Import is not complete; see the saved run and LOGS_DATAPULL_PRICEM"
            )
