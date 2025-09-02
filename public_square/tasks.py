from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import GovernmentAgency, Notification, TrendingTopic, User
from .services import WhatsAppService


@shared_task
def update_user_metrics():
    """Update user engagement metrics"""
    users = User.objects.filter(is_active=True)

    for user in users:
        user.update_engagement_metrics()

    return f"Updated metrics for {users.count()} users"


@shared_task
def update_agency_metrics():
    """Update agency performance metrics"""
    agencies = GovernmentAgency.objects.filter(is_active=True)

    for agency in agencies:
        agency.update_metrics()

    return f"Updated metrics for {agencies.count()} agencies"


@shared_task
def cleanup_old_data():
    """Clean up old notifications and trends"""

    # Delete old read notifications (older than 30 days)
    old_notifications = Notification.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=30), is_read=True
    )
    notifications_deleted = old_notifications.count()
    old_notifications.delete()

    # Deactivate old trending topics
    old_trends = TrendingTopic.objects.filter(
        last_updated__lt=timezone.now() - timedelta(days=7), count__lt=5
    )
    trends_updated = old_trends.update(is_active=False)

    return f"Deleted {notifications_deleted} notifications, deactivated {trends_updated} trends"


@shared_task
def send_whatsapp_notification(phone_number, message):
    """Send WhatsApp notification"""

    result = WhatsAppService.send_message(phone_number, message)
    return result
