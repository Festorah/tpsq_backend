from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from public_square.models import Notification, TrendingTopic


class CleanupOldDataCommand(BaseCommand):
    help = "Clean up old notifications and trends"

    def handle(self, *args, **options):
        # Delete old notifications (older than 30 days)
        old_notifications = Notification.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=30), is_read=True
        )
        notifications_deleted = old_notifications.count()
        old_notifications.delete()

        # Deactivate old trending topics (older than 7 days with low counts)
        old_trends = TrendingTopic.objects.filter(
            last_updated__lt=timezone.now() - timedelta(days=7), count__lt=5
        )
        trends_updated = old_trends.update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {notifications_deleted} old notifications and "
                f"deactivated {trends_updated} old trends"
            )
        )
