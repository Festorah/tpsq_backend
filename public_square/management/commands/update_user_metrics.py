from django.core.management.base import BaseCommand
from public_square.models import User


class UpdateUserMetricsCommand(BaseCommand):
    help = "Update user engagement metrics"

    def handle(self, *args, **options):
        users = User.objects.all()

        for user in users:
            user.update_engagement_metrics()

        self.stdout.write(
            self.style.SUCCESS(f"Updated metrics for {users.count()} users")
        )
