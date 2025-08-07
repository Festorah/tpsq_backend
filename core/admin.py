from django.contrib import admin

from .models import EarlyAccessSignup, QuestionnaireResponse


@admin.register(EarlyAccessSignup)
class EarlyAccessSignupAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "email",
        "area",
        "primary_issue",
        "likelihood_rating",
        "created_at",
    ]
    list_filter = [
        "area",
        "primary_issue",
        "wants_newsletter",
        "wants_beta_testing",
        "created_at",
    ]
    search_fields = ["name", "email", "phone"]
    readonly_fields = ["created_at", "ip_address", "user_agent"]

    fieldsets = (
        ("Personal Information", {"fields": ("name", "email", "phone")}),
        (
            "Location & Issues",
            {"fields": ("area", "primary_issue", "likelihood_rating")},
        ),
        ("Preferences", {"fields": ("wants_newsletter", "wants_beta_testing")}),
        (
            "System Info",
            {
                "fields": ("created_at", "ip_address", "user_agent"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(QuestionnaireResponse)
class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ["id", "area", "platform_interest", "is_completed", "created_at"]
    list_filter = [
        "fct_connection",
        "area",
        "platform_interest",
        "premium_willingness",
        "created_at",
    ]
    search_fields = ["email", "phone", "area"]
    readonly_fields = ["created_at", "completed_at", "ip_address", "user_agent"]

    fieldsets = (
        (
            "Demographics",
            {
                "fields": (
                    "fct_connection",
                    "area",
                    "age_range",
                    "occupation",
                    "education",
                )
            },
        ),
        (
            "Civic Issues Experience",
            {
                "fields": (
                    "civic_issues",
                    "issue_impact",
                    "tried_reporting",
                    "reporting_methods",
                    "reporting_outcome",
                    "government_satisfaction",
                )
            },
        ),
        (
            "Platform Interest",
            {"fields": ("platform_interest", "primary_reason", "concerns")},
        ),
        (
            "Usage & Payment",
            {
                "fields": (
                    "usage_frequency",
                    "platform_preference",
                    "premium_willingness",
                    "fair_price",
                )
            },
        ),
        (
            "Social & Sharing",
            {
                "fields": (
                    "recommendation_likelihood",
                    "recommend_to",
                    "ambassador_interest",
                    "update_preferences",
                )
            },
        ),
        (
            "Open Feedback",
            {
                "fields": (
                    "excitement_factor",
                    "biggest_worry",
                    "perfect_feature",
                    "additional_comments",
                )
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "wants_launch_notification",
                    "research_interests",
                    "phone",
                    "email",
                    "preferred_contact",
                )
            },
        ),
        (
            "System Info",
            {
                "fields": (
                    "created_at",
                    "completed_at",
                    "time_spent_seconds",
                    "ip_address",
                    "user_agent",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def is_completed(self, obj):
        return obj.is_completed()

    is_completed.boolean = True
    is_completed.short_description = "Completed"
