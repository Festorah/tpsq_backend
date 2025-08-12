from django.urls import path

from . import views

urlpatterns = [
    path("early-access/", views.submit_early_access, name="submit_early_access"),
    path("check-email/", views.check_email_exists, name="check_email_exists"),
    path("questionnaire/", views.submit_questionnaire, name="submit_questionnaire"),
    path("stats/", views.stats_summary, name="stats_summary"),
    # Frontend pages
    path("", views.LandingPageView.as_view(), name="landing_page"),  # Root landing page
    path("landing/", views.LandingPageView.as_view(), name="landing_page"),
    path(
        "facebook-ads/landing/",
        views.AdsLandingPageView.as_view(),
        name="ads_landing_page",
    ),
    path("survey/", views.QuestionnaireView.as_view(), name="questionnaire_page"),
]
