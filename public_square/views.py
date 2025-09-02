# views.py - Views and API endpoints

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import CreateView, DetailView, ListView

from .forms import CommentForm, IssueCreateForm, UserProfileForm, UserRegistrationForm
from .models import (
    Category,
    Comment,
    GovernmentAgency,
    Issue,
    Notification,
    TrendingTopic,
    User,
)
from .services import (
    AnalyticsService,
    CommentService,
    IssueService,
    NotificationService,
    TrendingService,
    WhatsAppService,
)

logger = logging.getLogger(__name__)


class UserRegistrationView(CreateView):
    """User registration view"""

    form_class = UserRegistrationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("public_square:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        # Log the user in after registration
        login(self.request, self.object)
        messages.success(
            self.request,
            "Welcome to The Public Square! Your account has been created successfully.",
        )
        return response


# Main Views
def home(request):
    """Main dashboard/homepage"""

    context = {
        "categories": Category.objects.filter(is_active=True).annotate(
            issue_count=Count("issues", filter=Q(issues__is_active=True))
        ),
        "trending_topics": TrendingService.get_trending_topics(limit=5),
        "dashboard_stats": AnalyticsService.get_dashboard_stats(),
    }

    if request.user.is_authenticated:
        context["user_notifications"] = NotificationService.get_user_notifications(
            request.user, unread_only=True
        )[
            :3
        ]  # Show only 3 recent notifications

    return render(request, "public_square/index.html", context)


@method_decorator(login_required, name="dispatch")
class IssueListView(ListView):
    """List view for issues with filtering"""

    model = Issue
    template_name = "public_square/issue_list.html"
    context_object_name = "issues"
    paginate_by = 20

    def get_queryset(self):
        filter_type = self.request.GET.get("filter", "all")
        category = self.request.GET.get("category")
        location = self.request.GET.get("location")
        status = self.request.GET.get("status")

        result = IssueService.get_filtered_issues(
            user=self.request.user,
            filter_type=filter_type,
            category=category,
            location=location,
            status=status,
            page_size=self.paginate_by,
            page=int(self.request.GET.get("page", 1)),
        )

        self.extra_context = {
            "filter_type": filter_type,
            "total_count": result["total_count"],
            "categories": Category.objects.filter(is_active=True),
            "agencies": GovernmentAgency.objects.filter(is_active=True),
        }

        return result["issues"]


class IssueDetailView(DetailView):
    """Detail view for individual issues"""

    model = Issue
    template_name = "public_square/issue_detail.html"
    context_object_name = "issue"

    def get_queryset(self):
        return (
            Issue.objects.select_related("author", "category", "assigned_agency")
            .prefetch_related(
                "images",
                "likes",
                "reposts",
                Prefetch("comments", queryset=Comment.objects.select_related("author")),
            )
            .filter(is_active=True)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        issue = self.object

        # Increment view count
        Issue.objects.filter(pk=issue.pk).update(views_count=F("views_count") + 1)

        context.update(
            {
                "comments": CommentService.get_issue_comments(issue),
                "comment_form": CommentForm(),
                "user_liked": (
                    issue.likes.filter(id=self.request.user.id).exists()
                    if self.request.user.is_authenticated
                    else False
                ),
                "user_reposted": (
                    issue.reposts.filter(id=self.request.user.id).exists()
                    if self.request.user.is_authenticated
                    else False
                ),
                "related_issues": Issue.objects.filter(
                    category=issue.category, is_active=True
                ).exclude(pk=issue.pk)[:5],
            }
        )

        return context


@login_required
def create_issue(request):
    """Create new issue"""

    if request.method == "POST":
        form = IssueCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Handle multiple images
                images = request.FILES.getlist("images")

                issue = IssueService.create_issue(
                    author=request.user,
                    title=form.cleaned_data["title"],
                    content=form.cleaned_data["content"],
                    category_slug=form.cleaned_data["category"].slug,
                    location=form.cleaned_data["location"],
                    latitude=form.cleaned_data.get("latitude"),
                    longitude=form.cleaned_data.get("longitude"),
                    images=images,
                )

                messages.success(request, "Issue created successfully!")
                return redirect("issue_detail", pk=issue.pk)

            except Exception as e:
                logger.error(f"Error creating issue: {str(e)}")
                messages.error(request, "Error creating issue. Please try again.")
    else:
        form = IssueCreateForm()

    return render(
        request,
        "public_square/create_issue.html",
        {"form": form, "categories": Category.objects.filter(is_active=True)},
    )


# API Views
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_issues(request):
    """API endpoint for issues"""

    if request.method == "GET":
        filter_type = request.GET.get("filter", "all")
        category = request.GET.get("category")
        location = request.GET.get("location")
        page = int(request.GET.get("page", 1))

        result = IssueService.get_filtered_issues(
            user=request.user if request.user.is_authenticated else None,
            filter_type=filter_type,
            category=category,
            location=location,
            page=page,
        )

        # Serialize issues
        issues_data = []
        for issue in result["issues"]:
            issue_data = {
                "id": str(issue.id),
                "title": issue.title,
                "content": issue.content,
                "author": {
                    "name": issue.author.full_name,
                    "initials": issue.author.initials,
                },
                "category": issue.category.name if issue.category else None,
                "status": issue.status,
                "status_display": issue.get_status_display(),
                "location": issue.location,
                "time_ago": issue.time_ago,
                "likes_count": issue.likes_count,
                "reposts_count": issue.reposts_count,
                "comments_count": issue.comments_count,
                "assigned_agency": (
                    issue.assigned_agency.name if issue.assigned_agency else None
                ),
                "source": issue.source,
                "is_urgent": issue.is_urgent,
                "images": [
                    {"url": img.image.url, "caption": img.caption}
                    for img in issue.images.all()
                ],
            }

            # Add user-specific data if authenticated
            if request.user.is_authenticated:
                issue_data.update(
                    {
                        "user_liked": issue.likes.filter(id=request.user.id).exists(),
                        "user_reposted": issue.reposts.filter(
                            id=request.user.id
                        ).exists(),
                    }
                )

            issues_data.append(issue_data)

        return JsonResponse(
            {
                "status": "success",
                "issues": issues_data,
                "pagination": {
                    "page": result["page"],
                    "page_size": result["page_size"],
                    "total_count": result["total_count"],
                    "has_next": result["has_next"],
                    "has_prev": result["has_prev"],
                },
            }
        )

    elif request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse(
                {"status": "error", "message": "Authentication required"}, status=401
            )

        try:
            data = json.loads(request.body)

            issue = IssueService.create_issue(
                author=request.user,
                title=data.get("title", ""),
                content=data.get("content", ""),
                category_slug=data.get("category", ""),
                location=data.get("location", ""),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Issue created successfully",
                    "issue_id": str(issue.id),
                }
            )

        except Exception as e:
            logger.error(f"API error creating issue: {str(e)}")
            return JsonResponse(
                {"status": "error", "message": "Error creating issue"}, status=400
            )


@login_required
@require_POST
@csrf_exempt
def api_toggle_like(request, issue_id):
    """Toggle like on an issue"""

    try:
        issue = get_object_or_404(Issue, id=issue_id, is_active=True)
        result = IssueService.toggle_like(issue, request.user)

        return JsonResponse({"status": "success", **result})

    except Exception as e:
        logger.error(f"Error toggling like: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": "Error updating like"}, status=400
        )


@login_required
@require_POST
@csrf_exempt
def api_toggle_repost(request, issue_id):
    """Toggle repost on an issue"""

    try:
        issue = get_object_or_404(Issue, id=issue_id, is_active=True)
        data = json.loads(request.body) if request.body else {}
        comment = data.get("comment", "")

        result = IssueService.toggle_repost(issue, request.user, comment)

        return JsonResponse({"status": "success", **result})

    except Exception as e:
        logger.error(f"Error toggling repost: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": "Error updating repost"}, status=400
        )


@login_required
@require_POST
@csrf_exempt
def api_create_comment(request, issue_id):
    """Create a comment on an issue"""

    try:
        issue = get_object_or_404(Issue, id=issue_id, is_active=True)
        data = json.loads(request.body)

        content = data.get("content", "").strip()
        if not content:
            return JsonResponse(
                {"status": "error", "message": "Comment content is required"},
                status=400,
            )

        parent_comment_id = data.get("parent_comment_id")
        parent_comment = None
        if parent_comment_id:
            parent_comment = get_object_or_404(Comment, id=parent_comment_id)

        comment = CommentService.create_comment(
            issue=issue,
            author=request.user,
            content=content,
            parent_comment=parent_comment,
        )

        return JsonResponse(
            {
                "status": "success",
                "comment": {
                    "id": str(comment.id),
                    "content": comment.content,
                    "author": {
                        "name": comment.author.full_name,
                        "initials": comment.author.initials,
                    },
                    "time_ago": comment.time_ago,
                    "likes_count": comment.likes_count,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": "Error creating comment"}, status=400
        )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """WhatsApp webhook endpoint"""

    if request.method == "GET":
        # Webhook verification
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        verification_result = WhatsAppService.verify_webhook(mode, token, challenge)

        if verification_result:
            return HttpResponse(verification_result)
        else:
            return HttpResponse("Verification failed", status=403)

    elif request.method == "POST":
        # Process incoming message
        try:
            data = json.loads(request.body)
            result = WhatsAppService.process_incoming_message(data)

            logger.info(f"WhatsApp webhook result: {result}")

            return JsonResponse({"status": "success", "message": "Message processed"})

        except Exception as e:
            logger.error(f"WhatsApp webhook error: {str(e)}")
            return JsonResponse(
                {"status": "error", "message": "Error processing message"}, status=400
            )


@login_required
def api_notifications(request):
    """Get user notifications"""

    notifications = NotificationService.get_user_notifications(request.user)

    notifications_data = [
        {
            "id": str(notif.id),
            "type": notif.notification_type,
            "title": notif.title,
            "message": notif.message,
            "is_read": notif.is_read,
            "created_at": notif.created_at.isoformat(),
            "issue_id": str(notif.issue.id) if notif.issue else None,
        }
        for notif in notifications
    ]

    return JsonResponse({"status": "success", "notifications": notifications_data})


@login_required
@require_POST
def api_mark_notification_read(request, notification_id):
    """Mark notification as read"""

    try:
        notification = get_object_or_404(
            Notification, id=notification_id, recipient=request.user
        )
        NotificationService.mark_as_read(notification)

        return JsonResponse({"status": "success"})

    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": "Error updating notification"}, status=400
        )


def api_categories(request):
    """Get all categories"""

    categories = Category.objects.filter(is_active=True).annotate(
        total_issues=Count("issues", filter=Q(issues__is_active=True))
    )

    categories_data = [
        {
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "icon_class": cat.icon_class,
            "color": cat.color,
            "issue_count": cat.total_issues,
        }
        for cat in categories
    ]

    return JsonResponse({"status": "success", "categories": categories_data})


def api_trending_topics(request):
    """Get trending topics"""

    location = request.GET.get("location", "")
    topics = TrendingService.get_trending_topics(location=location)

    topics_data = [
        {"tag": topic.tag, "count": topic.count, "location": topic.location}
        for topic in topics
    ]

    return JsonResponse({"status": "success", "trending_topics": topics_data})


def api_dashboard_stats(request):
    """Get dashboard statistics"""

    stats = AnalyticsService.get_dashboard_stats()

    return JsonResponse({"status": "success", "stats": stats})


# User Profile Views
@login_required
def user_profile(request):
    """User profile view"""

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("user_profile")
    else:
        form = UserProfileForm(instance=request.user)

    user_issues = Issue.objects.filter(author=request.user, is_active=True).order_by(
        "-created_at"
    )[:10]

    context = {
        "form": form,
        "user_issues": user_issues,
        "user_stats": {
            "issues_posted": request.user.issues_posted,
            "issues_resolved": request.user.issues_resolved,
            "community_impact": request.user.community_impact_score,
        },
    }

    return render(request, "public_square/user_profile.html", context)


# Error Handlers
def handler404(request, exception):
    return render(request, "public_square/404.html", status=404)


def handler500(request):
    return render(request, "public_square/500.html", status=500)


# CSRF Token for AJAX requests
def csrf_token_view(request):
    """Provide CSRF token for AJAX requests"""
    return JsonResponse({"csrfToken": get_token(request)})


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring"""
    try:
        # Check database
        User.objects.count()

        # Check Redis
        from django.core.cache import cache

        cache.set("health_check", "ok", 30)
        cache.get("health_check")

        return JsonResponse(
            {
                "status": "healthy",
                "timestamp": timezone.now().isoformat(),
                "services": {"database": "ok", "cache": "ok"},
            }
        )
    except Exception as e:
        return JsonResponse({"status": "unhealthy", "error": str(e)}, status=500)


@require_http_methods(["GET"])
def api_issue_comments(request, issue_id):
    """Get comments for a specific issue"""

    try:
        issue = get_object_or_404(Issue, id=issue_id, is_active=True)
        comments = CommentService.get_issue_comments(issue)

        comments_data = []
        for comment in comments:
            comment_data = {
                "id": str(comment.id),
                "content": comment.content,
                "author": {
                    "name": comment.author.full_name,
                    "initials": comment.author.initials,
                },
                "time_ago": comment.time_ago,
                "likes_count": comment.likes_count,
                "created_at": comment.created_at.isoformat(),
            }

            # Add user-specific data if authenticated
            if request.user.is_authenticated:
                comment_data["user_liked"] = comment.likes.filter(
                    id=request.user.id
                ).exists()

            comments_data.append(comment_data)

        return JsonResponse(
            {
                "status": "success",
                "comments": comments_data,
                "total_count": len(comments_data),
            }
        )

    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": "Error fetching comments"}, status=400
        )
