from .models import Category, TrendingTopic
from .services import AnalyticsService


def global_context(request):
    """Global context processor for common data"""

    context = {
        "site_name": "The Public Square",
        "whatsapp_number": "+234 800 1234 567",
    }

    # Add categories for all pages
    try:
        context["global_categories"] = Category.objects.filter(is_active=True)[:6]
    except:
        context["global_categories"] = []

    # Add trending topics
    try:
        context["global_trending"] = TrendingTopic.objects.filter(is_active=True)[:5]
    except:
        context["global_trending"] = []

    # Add user notifications count if authenticated
    if request.user.is_authenticated:
        try:
            context["unread_notifications_count"] = request.user.notifications.filter(
                is_read=False
            ).count()
        except:
            context["unread_notifications_count"] = 0

    return context
