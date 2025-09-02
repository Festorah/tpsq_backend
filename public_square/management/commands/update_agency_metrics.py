from django.core.management.base import BaseCommand
from public_square.models import GovernmentAgency


class UpdateAgencyMetricsCommand(BaseCommand):
    help = "Update government agency performance metrics"

    def handle(self, *args, **options):
        agencies = GovernmentAgency.objects.filter(is_active=True)

        for agency in agencies:
            agency.update_metrics()

        self.stdout.write(
            self.style.SUCCESS(f"Updated metrics for {agencies.count()} agencies")
        )
