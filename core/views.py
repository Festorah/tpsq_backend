import logging

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import EarlyAccessSignup, QuestionnaireResponse
from .serializers import EarlyAccessSignupSerializer, QuestionnaireResponseSerializer

# Set up logging
logger = logging.getLogger(__name__)


class LandingPageView(TemplateView):
    """Serve the landing page directly from Django"""

    template_name = "core/new_landing.html"


class UnconcernedLandingPageView(TemplateView):
    """Serve the landing page directly from Django"""

    template_name = "core/unconcerned.html"


class FrustratedActivistLandingPageView(TemplateView):
    """Serve the landing page directly from Django"""

    template_name = "core/frustrated_activists_page.html"


class ConcernedParentsLandingPageView(TemplateView):
    """Serve the landing page directly from Django"""

    template_name = "core/concerned_parents_page.html"


class HopefulChangeMakersLandingPageView(TemplateView):
    """Serve the landing page directly from Django"""

    template_name = "core/hopeful_changemakers_page.html"


class QuestionnaireView(TemplateView):
    """Serve the questionnaire directly from Django"""

    template_name = "core/questionnaire.html"


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def submit_early_access(request):
    """Handle early access form submissions with duplicate prevention"""

    try:
        client_ip = get_client_ip(request)
        logger.info(f"[EARLY-ACCESS] Form submission received from IP: {client_ip}")
        logger.debug(f"[EARLY-ACCESS] Request data: {request.data}")

        # Map frontend field names to model field names
        data = request.data.copy()
        field_mapping = {
            "issue": "primary_issue",
            "likelihood": "likelihood_rating",
            "newsletter": "wants_newsletter",
            "beta_testing": "wants_beta_testing",
        }

        for old_key, new_key in field_mapping.items():
            if old_key in data:
                data[new_key] = data.pop(old_key)

        # Extract email for duplicate checking
        email = data.get("email", "").lower().strip()
        if not email:
            logger.warning("[VALIDATION-ERROR] No email provided")
            return Response(
                {
                    "success": False,
                    "errors": {"email": ["Email is required."]},
                    "error": "Email is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for existing email (MAIN DUPLICATE PREVENTION)
        existing_signup = EarlyAccessSignup.objects.filter(email__iexact=email).first()
        if existing_signup:
            logger.warning(
                f"[DUPLICATE-EMAIL] Attempt to register existing email: {email}"
            )
            return Response(
                {
                    "success": False,
                    "duplicate": True,
                    "error": f"The email '{email}' is already registered for early access.",
                    "errors": {
                        "email": [
                            f"The email '{email}' is already registered for early access."
                        ]
                    },
                    "existing_id": existing_signup.id,
                    "message": "This email address has already been registered.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rate limiting check (optional - can be disabled for testing)
        recent_submissions = EarlyAccessSignup.objects.filter(
            ip_address=client_ip
        ).count()
        if recent_submissions >= 10:  # Increased limit for testing
            logger.warning(f"[RATE-LIMIT] Too many submissions from IP: {client_ip}")
            return Response(
                {
                    "success": False,
                    "rate_limited": True,
                    "error": "Too many submissions from this location. Please try again later.",
                    "message": "Rate limit exceeded.",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Validate with serializer
        serializer = EarlyAccessSignupSerializer(data=data)

        if serializer.is_valid():
            try:
                # Save the new signup
                signup = serializer.save(
                    ip_address=client_ip,
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )

                logger.info(
                    f"[SUCCESS] Early access signup for {signup.email} (ID: {signup.id})"
                )

                # Return success response with all expected fields
                return Response(
                    {
                        "success": True,
                        "message": "Early access signup successful!",
                        "id": signup.id,
                        "email": signup.email,
                        "area": signup.area,
                        "name": signup.name,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except Exception as db_error:
                logger.error(
                    f"[DATABASE-ERROR] Error saving signup: {str(db_error)}",
                    exc_info=True,
                )
                return Response(
                    {
                        "success": False,
                        "error": "Database error occurred. Please try again.",
                        "message": "Unable to save your information.",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            # Serializer validation failed
            logger.warning(f"[VALIDATION-ERROR] Invalid form data: {serializer.errors}")
            return Response(
                {
                    "success": False,
                    "errors": serializer.errors,
                    "error": "Please check your form data and try again.",
                    "message": "Form validation failed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(
            f"[ERROR] Unexpected error in early access submission: {str(e)}",
            exc_info=True,
        )
        return Response(
            {
                "success": False,
                "error": "An unexpected error occurred. Please try again.",
                "message": "Server error occurred.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def check_email_exists(request):
    """Check if an email is already registered (for frontend validation)"""

    email = request.data.get("email", "").lower().strip()
    if not email:
        return Response({"exists": False})

    exists = EarlyAccessSignup.objects.filter(email__iexact=email).exists()

    return Response({"exists": exists, "email": email})


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def submit_questionnaire(request):
    """Handle questionnaire survey submissions"""

    try:
        logger.info(
            f"[QUESTIONNAIRE] Submission received from IP: {get_client_ip(request)}"
        )

        data = request.data.copy()
        responses = data.get("responses", {})

        mapped_data = {
            # Demographics
            "fct_connection": responses.get("q1", ""),
            "area": responses.get("q2", ""),
            "age_range": responses.get("q3", ""),
            "occupation": responses.get("q4", ""),
            "education": responses.get("q5", ""),
            # Civic Issues
            "civic_issues": responses.get("q6", []),
            "issue_impact": responses.get("q7", ""),
            "tried_reporting": responses.get("q8", ""),
            "reporting_methods": responses.get("q9", []),
            "reporting_outcome": responses.get("q10", ""),
            "government_satisfaction": responses.get("q11", ""),
            # Platform Interest
            "platform_interest": responses.get("q13", ""),
            "primary_reason": responses.get("q14", ""),
            "concerns": responses.get("q17", []),
            # Usage Preferences
            "usage_frequency": responses.get("q18", ""),
            "platform_preference": responses.get("q19", ""),
            "premium_willingness": responses.get("q20", ""),
            "fair_price": responses.get("q21", ""),
            # Social
            "recommendation_likelihood": responses.get("q23", ""),
            "recommend_to": responses.get("q24", []),
            "ambassador_interest": responses.get("q25", ""),
            "update_preferences": responses.get("q26", []),
            # Feedback
            "excitement_factor": responses.get("q27", ""),
            "biggest_worry": responses.get("q28", ""),
            "perfect_feature": responses.get("q29", ""),
            "additional_comments": responses.get("q30", ""),
            # Contact
            "wants_launch_notification": responses.get("q31", ""),
            "research_interests": responses.get("q33", []),
            "phone": responses.get("phone", ""),
            "email": responses.get("email", ""),
            "preferred_contact": responses.get("contact_method", ""),
            # Meta
            "time_spent_seconds": data.get("time_spent", None),
        }

        serializer = QuestionnaireResponseSerializer(data=mapped_data)

        if serializer.is_valid():
            response = serializer.save(
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            logger.info(
                f"[SUCCESS] Questionnaire submitted successfully (ID: {response.id})"
            )

            return Response(
                {
                    "success": True,
                    "message": "Questionnaire submitted successfully!",
                    "id": response.id,
                },
                status=status.HTTP_201_CREATED,
            )

        logger.warning(
            f"[VALIDATION-ERROR] Invalid questionnaire data: {serializer.errors}"
        )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        logger.error(
            f"[ERROR] Unexpected error in questionnaire submission: {str(e)}",
            exc_info=True,
        )
        return Response(
            {
                "success": False,
                "error": "An unexpected error occurred. Please try again.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def stats_summary(request):
    """Simple stats endpoint for monitoring"""

    try:
        early_access_count = EarlyAccessSignup.objects.count()
        questionnaire_count = QuestionnaireResponse.objects.count()
        completed_questionnaires = QuestionnaireResponse.objects.filter(
            completed_at__isnull=False
        ).count()

        logger.info(
            f"[STATS] Retrieved stats - EA: {early_access_count}, Q: {questionnaire_count}"
        )

        return Response(
            {
                "early_access_signups": early_access_count,
                "questionnaire_responses": questionnaire_count,
                "completed_questionnaires": completed_questionnaires,
            }
        )

    except Exception as e:
        logger.error(f"[ERROR] Error retrieving stats: {str(e)}", exc_info=True)
        return Response(
            {"error": "Unable to retrieve stats"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
