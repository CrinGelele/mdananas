from django.core.management.base import BaseCommand, CommandError

from datapull_service.pricem.bindings import bind_product
from datapull_service.pricem.errors import safe_error
from datapull_service.pricem.schema import verify_schema


class Command(BaseCommand):
    help = "Bind a saved Priceva product to a chosen monitoring row, preserving its mapping."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, required=True)
        parser.add_argument("--client-code", required=True)
        parser.add_argument("--kind", choices=("int", "ext"), required=True)
        parser.add_argument("--product-id", type=int, required=True)
        parser.add_argument(
            "--check", action="store_true", help="Preview without writes"
        )

    def handle(self, *args, **options):
        try:
            verify_schema()
            plan = bind_product(
                options["run"],
                options["client_code"],
                options["kind"],
                options["product_id"],
                check_only=options["check"],
            )
        except Exception as error:
            raise CommandError(safe_error(error)) from None
        state = (
            "check"
            if options["check"]
            else "bound"
            if plan.changed
            else "already bound"
        )
        self.stdout.write(
            f"{state}: run={plan.run_id}; client_code={plan.client_code}; "
            f"Priceva ID={plan.priceva_id}; target={plan.kind}:{plan.product_id}; "
            f"mapping={plan.mapping}"
        )
