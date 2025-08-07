import json

from django.db import models
from django.utils import timezone


class EarlyAccessSignup(models.Model):
    """Model for landing page early access signups"""

    # Personal Info
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    # Location & Issue
    area = models.CharField(max_length=50)
    primary_issue = models.CharField(max_length=50)

    # Engagement
    likelihood_rating = models.IntegerField(help_text="1-10 scale")
    wants_newsletter = models.BooleanField(default=False)
    wants_beta_testing = models.BooleanField(default=False)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Early Access Signup"
        verbose_name_plural = "Early Access Signups"

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.area}"


class QuestionnaireResponse(models.Model):
    """Model for questionnaire survey responses"""

    # Demographics (Step 1)
    fct_connection = models.CharField(max_length=20, help_text="live, work, study, no")
    area = models.CharField(max_length=50, blank=True)
    age_range = models.CharField(max_length=10, blank=True)
    occupation = models.CharField(max_length=30, blank=True)
    education = models.CharField(max_length=30, blank=True)

    # Civic Issues Experience (Step 2)
    civic_issues = models.JSONField(
        default=list, help_text="Array of experienced issues"
    )
    issue_impact = models.CharField(max_length=2, blank=True, help_text="1-5 scale")
    tried_reporting = models.CharField(max_length=20, blank=True)
    reporting_methods = models.JSONField(
        default=list, help_text="How they tried to report"
    )
    reporting_outcome = models.CharField(max_length=30, blank=True)
    government_satisfaction = models.CharField(
        max_length=2, blank=True, help_text="1-10 scale"
    )

    # Platform Interest (Step 3)
    platform_interest = models.CharField(max_length=20, blank=True)
    primary_reason = models.CharField(max_length=30, blank=True)
    concerns = models.JSONField(default=list, help_text="Platform concerns")

    # Usage Preferences (Step 4)
    usage_frequency = models.CharField(max_length=20, blank=True)
    platform_preference = models.CharField(max_length=20, blank=True)
    premium_willingness = models.CharField(max_length=20, blank=True)
    fair_price = models.CharField(max_length=20, blank=True)

    # Social Sharing (Step 5)
    recommendation_likelihood = models.CharField(
        max_length=2, blank=True, help_text="1-10 scale"
    )
    recommend_to = models.JSONField(default=list, help_text="Who they'd recommend to")
    ambassador_interest = models.CharField(max_length=20, blank=True)
    update_preferences = models.JSONField(
        default=list, help_text="How to receive updates"
    )

    # Open Feedback (Step 6)
    excitement_factor = models.TextField(blank=True, max_length=200)
    biggest_worry = models.TextField(blank=True, max_length=200)
    perfect_feature = models.TextField(blank=True, max_length=150)
    additional_comments = models.TextField(blank=True, max_length=300)

    # Contact & Follow-up (Step 7)
    wants_launch_notification = models.CharField(max_length=20, blank=True)
    research_interests = models.JSONField(
        default=list, help_text="Beta testing, focus groups, etc"
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    preferred_contact = models.CharField(max_length=20, blank=True)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    time_spent_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Questionnaire Response"
        verbose_name_plural = "Questionnaire Responses"

    def __str__(self):
        return (
            f"Response {self.id} - {self.area} - {self.created_at.strftime('%Y-%m-%d')}"
        )

    def is_completed(self):
        return self.completed_at is not None

    def get_completion_time_minutes(self):
        if self.time_spent_seconds:
            return round(self.time_spent_seconds / 60, 1)
        return None
