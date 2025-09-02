from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    AgencyResponse,
    Category,
    Comment,
    GovernmentAgency,
    Issue,
    IssueImage,
    Like,
    Notification,
    Repost,
    TrendingTopic,
    User,
    WhatsAppMessage,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin"""

    list_display = [
        "username",
        "email",
        "full_name",
        "user_type",
        "location",
        "is_verified",
        "issues_posted",
        "community_impact_score",
        "date_joined",
    ]
    list_filter = ["user_type", "is_verified", "is_active", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name", "phone_number"]
    ordering = ["-date_joined"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Additional Info",
            {
                "fields": (
                    "user_type",
                    "phone_number",
                    "location",
                    "bio",
                    "avatar",
                    "is_verified",
                )
            },
        ),
        (
            "Engagement Metrics",
            {
                "fields": (
                    "issues_posted",
                    "issues_resolved",
                    "community_impact_score",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def full_name(self, obj):
        return obj.full_name

    full_name.short_description = "Full Name"

    actions = ["verify_users", "update_metrics"]

    def verify_users(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} users verified successfully.")

    verify_users.short_description = "Verify selected users"

    def update_metrics(self, request, queryset):
        count = 0
        for user in queryset:
            user.update_engagement_metrics()
            count += 1
        self.message_user(request, f"Metrics updated for {count} users.")

    update_metrics.short_description = "Update engagement metrics"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category Admin"""

    list_display = [
        "name",
        "slug",
        "icon_class",
        "color_display",
        "issue_count_display",
        "is_active",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}

    def color_display(self, obj):
        return format_html(
            '<div style="background-color: {}; width: 30px; height: 20px; border-radius: 4px;"></div>',
            obj.color,
        )

    color_display.short_description = "Color"

    def issue_count_display(self, obj):
        return obj.issue_count

    issue_count_display.short_description = "Issues"


@admin.register(GovernmentAgency)
class GovernmentAgencyAdmin(admin.ModelAdmin):
    """Government Agency Admin"""

    list_display = [
        "name",
        "abbreviation",
        "contact_email",
        "resolution_rate",
        "average_response_time",
        "is_active",
    ]
    list_filter = ["is_active", "handled_categories"]
    search_fields = ["name", "abbreviation", "contact_email"]
    filter_horizontal = ["handled_categories"]

    actions = ["update_metrics"]

    def update_metrics(self, request, queryset):
        count = 0
        for agency in queryset:
            agency.update_metrics()
            count += 1
        self.message_user(request, f"Metrics updated for {count} agencies.")

    update_metrics.short_description = "Update performance metrics"


class IssueImageInline(admin.TabularInline):
    """Inline for Issue Images"""

    model = IssueImage
    extra = 1
    readonly_fields = ["uploaded_at"]


class CommentInline(admin.TabularInline):
    """Inline for Comments"""

    model = Comment
    extra = 0
    readonly_fields = ["created_at"]
    fields = ["author", "content", "created_at", "is_active"]


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    """Enhanced Issue Admin"""

    list_display = [
        "issue_number",
        "title_short",
        "author",
        "category",
        "status",
        "location",
        "source",
        "likes_count",
        "created_at",
    ]
    list_filter = [
        "status",
        "category",
        "source",
        "is_urgent",
        "is_featured",
        "created_at",
        "assigned_agency",
    ]
    search_fields = ["title", "content", "author__username", "location"]
    readonly_fields = ["created_at", "updated_at", "views_count", "issue_number"]
    date_hierarchy = "created_at"

    fieldsets = [
        (
            "Basic Information",
            {
                "fields": [
                    "title",
                    "content",
                    "author",
                    "category",
                    "location",
                    "latitude",
                    "longitude",
                ]
            },
        ),
        (
            "Status & Assignment",
            {
                "fields": [
                    "status",
                    "assigned_agency",
                    "agency_assigned_at",
                    "agency_response_time",
                    "resolved_at",
                ]
            },
        ),
        (
            "Metadata",
            {
                "fields": ["source", "is_urgent", "is_featured", "is_active"],
                "classes": ["collapse"],
            },
        ),
        (
            "WhatsApp Integration",
            {
                "fields": ["whatsapp_message_id", "whatsapp_sender_number"],
                "classes": ["collapse"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at", "views_count", "issue_number"],
                "classes": ["collapse"],
            },
        ),
    ]

    inlines = [IssueImageInline, CommentInline]

    def title_short(self, obj):
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title

    title_short.short_description = "Title"

    def likes_count(self, obj):
        return obj.likes_count

    likes_count.short_description = "Likes"

    def issue_number(self, obj):
        return obj.issue_number

    issue_number.short_description = "Issue #"

    actions = ["mark_resolved", "mark_in_progress", "feature_issues", "assign_agencies"]

    def mark_resolved(self, request, queryset):
        count = 0
        for issue in queryset:
            issue.mark_resolved()
            count += 1
        self.message_user(request, f"{count} issues marked as resolved.")

    mark_resolved.short_description = "Mark as resolved"

    def mark_in_progress(self, request, queryset):
        count = queryset.update(status="in_progress")
        self.message_user(request, f"{count} issues marked as in progress.")

    mark_in_progress.short_description = "Mark as in progress"

    def feature_issues(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} issues featured.")

    feature_issues.short_description = "Feature selected issues"

    def assign_agencies(self, request, queryset):
        count = 0
        for issue in queryset:
            if issue.assign_to_agency():
                count += 1
        self.message_user(request, f"{count} issues assigned to agencies.")

    assign_agencies.short_description = "Auto-assign to agencies"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Comment Admin"""

    list_display = [
        "id",
        "author",
        "issue_short",
        "content_short",
        "created_at",
        "is_active",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["content", "author__username"]
    readonly_fields = ["created_at", "updated_at"]

    def issue_short(self, obj):
        return f"#{obj.issue.issue_number}: {obj.issue.title[:30]}..."

    issue_short.short_description = "Issue"

    def content_short(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_short.short_description = "Content"


@admin.register(AgencyResponse)
class AgencyResponseAdmin(admin.ModelAdmin):
    """Agency Response Admin"""

    list_display = ["agency", "issue_short", "responder", "is_public", "created_at"]
    list_filter = ["agency", "is_public", "created_at"]
    search_fields = ["content", "issue__title"]
    readonly_fields = ["created_at"]

    def issue_short(self, obj):
        return f"#{obj.issue.issue_number}: {obj.issue.title[:30]}..."

    issue_short.short_description = "Issue"


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    """WhatsApp Message Admin"""

    list_display = [
        "message_id",
        "phone_number",
        "message_type",
        "user",
        "is_processed",
        "created_at",
    ]
    list_filter = ["message_type", "is_processed", "created_at"]
    search_fields = ["phone_number", "content", "message_id"]
    readonly_fields = ["created_at"]

    actions = ["reprocess_messages"]

    def reprocess_messages(self, request, queryset):
        count = queryset.filter(is_processed=False).count()
        # Here you would implement reprocessing logic
        self.message_user(request, f"{count} messages queued for reprocessing.")

    reprocess_messages.short_description = "Reprocess unprocessed messages"


@admin.register(TrendingTopic)
class TrendingTopicAdmin(admin.ModelAdmin):
    """Trending Topic Admin"""

    list_display = ["tag", "location", "count", "is_active", "last_updated"]
    list_filter = ["is_active", "location", "last_updated"]
    search_fields = ["tag", "location"]
    readonly_fields = ["last_updated"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification Admin"""

    list_display = ["recipient", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["title", "message", "recipient__username"]
    readonly_fields = ["created_at"]

    actions = ["mark_as_read"]

    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f"{count} notifications marked as read.")

    mark_as_read.short_description = "Mark as read"


# Dashboard customization
admin.site.site_header = "The Public Square Administration"
admin.site.site_title = "Public Square Admin"
admin.site.index_title = "FCT Civic Platform Administration"
