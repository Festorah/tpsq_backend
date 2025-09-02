from django.contrib.auth import views as auth_views
from django.urls import include, path

from . import views

app_name = "public_square"

urlpatterns = [
    # Main views
    path("", views.home, name="home"),
    path("issues/", views.IssueListView.as_view(), name="issue_list"),
    path("issues/<uuid:pk>/", views.IssueDetailView.as_view(), name="issue_detail"),
    path("issues/create/", views.create_issue, name="create_issue"),
    # User profile
    path("profile/", views.user_profile, name="user_profile"),
    # API endpoints
    path("api/issues/", views.api_issues, name="api_issues"),
    path(
        "api/issues/<uuid:issue_id>/like/",
        views.api_toggle_like,
        name="api_toggle_like",
    ),
    path(
        "api/issues/<uuid:issue_id>/repost/",
        views.api_toggle_repost,
        name="api_toggle_repost",
    ),
    path(
        "api/issues/<uuid:issue_id>/comments/",
        views.api_create_comment,
        name="api_create_comment",
    ),
    path(
        "api/issues/<uuid:issue_id>/comments/list/",
        views.api_issue_comments,
        name="api_issue_comments",
    ),
    path("api/notifications/", views.api_notifications, name="api_notifications"),
    path(
        "api/notifications/<uuid:notification_id>/read/",
        views.api_mark_notification_read,
        name="api_mark_notification_read",
    ),
    path("api/categories/", views.api_categories, name="api_categories"),
    path("api/trending/", views.api_trending_topics, name="api_trending_topics"),
    path("api/stats/", views.api_dashboard_stats, name="api_dashboard_stats"),
    path("api/csrf/", views.csrf_token_view, name="csrf_token"),
    # WhatsApp webhook
    path("webhooks/whatsapp/", views.whatsapp_webhook, name="whatsapp_webhook"),
    # Authentication URLs
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.UserRegistrationView.as_view(), name="signup"),
    path(
        "accounts/password_change/",
        auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "accounts/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "accounts/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
