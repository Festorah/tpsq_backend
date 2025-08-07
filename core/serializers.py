from django.utils import timezone
from rest_framework import serializers

from .models import EarlyAccessSignup, QuestionnaireResponse


class EarlyAccessSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = EarlyAccessSignup
        fields = [
            "name",
            "phone",
            "email",
            "area",
            "primary_issue",
            "likelihood_rating",
            "wants_newsletter",
            "wants_beta_testing",
        ]

    def validate_likelihood_rating(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError("Rating must be between 1 and 10")
        return value


class QuestionnaireResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionnaireResponse
        fields = "__all__"
        read_only_fields = ["created_at", "completed_at", "ip_address", "user_agent"]

    def create(self, validated_data):
        validated_data["completed_at"] = timezone.now()
        return super().create(validated_data)
