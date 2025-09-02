# models.py - Domain Models for The Public Square

import uuid
from datetime import datetime, timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

# from enum import Choices


class User(AbstractUser):
    """Extended user model for platform users"""

    class UserType(models.TextChoices):
        CITIZEN = "citizen", "Citizen"
        OFFICIAL = "official", "Government Official"
        AGENCY = "agency", "Agency Representative"
        ADMIN = "admin", "Administrator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(
        max_length=20, choices=UserType.choices, default=UserType.CITIZEN
    )
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(r"^\+?234\d{10}$", "Enter a valid Nigerian phone number")
        ],
    )
    location = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Engagement metrics
    issues_posted = models.PositiveIntegerField(default=0)
    issues_resolved = models.PositiveIntegerField(default=0)
    community_impact_score = models.PositiveIntegerField(default=0)

    @property
    def initials(self):
        """Generate user initials for avatar display"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    @property
    def full_name(self):
        """Get user's full name or username as fallback"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def update_engagement_metrics(self):
        """Update user engagement metrics"""
        self.issues_posted = self.posted_issues.count()
        self.issues_resolved = self.posted_issues.filter(status="resolved").count()
        self.community_impact_score = self.calculate_impact_score()
        self.save(
            update_fields=["issues_posted", "issues_resolved", "community_impact_score"]
        )

    def calculate_impact_score(self):
        """Calculate user's community impact score"""
        # Weight different actions differently
        posts_score = self.posted_issues.count() * 5
        likes_received = (
            sum(issue.likes.count() for issue in self.posted_issues.all()) * 2
        )
        comments_made = self.comments.count() * 1
        resolved_issues = self.posted_issues.filter(status="resolved").count() * 10

        return posts_score + likes_received + comments_made + resolved_issues


class Category(models.Model):
    """Issue categories for classification"""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(max_length=200)
    icon_class = models.CharField(max_length=50, help_text="FontAwesome icon class")
    color = models.CharField(
        max_length=7, default="#1d4ed8", help_text="Hex color code"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def issue_count(self):
        """Get count of issues in this category"""
        return self.issues.filter(is_active=True).count()


class GovernmentAgency(models.Model):
    """Government agencies responsible for different issue types"""

    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20)
    description = models.TextField()
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)
    website = models.URLField(blank=True)

    # Assign agencies to handle specific categories
    handled_categories = models.ManyToManyField(Category, related_name="agencies")

    # Performance metrics
    average_response_time = models.DurationField(null=True, blank=True)
    resolution_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "government agencies"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

    def update_metrics(self):
        """Update agency performance metrics"""
        assigned_issues = self.assigned_issues.filter(is_active=True)

        if assigned_issues.exists():
            # Calculate resolution rate
            resolved_count = assigned_issues.filter(status="resolved").count()
            self.resolution_rate = (resolved_count / assigned_issues.count()) * 100

            # Calculate average response time
            responded_issues = assigned_issues.exclude(
                agency_response_time__isnull=True
            )
            if responded_issues.exists():
                total_response_time = sum(
                    (issue.agency_response_time - issue.created_at).total_seconds()
                    for issue in responded_issues
                )
                avg_seconds = total_response_time / responded_issues.count()
                self.average_response_time = timedelta(seconds=avg_seconds)

        self.save(update_fields=["resolution_rate", "average_response_time"])


class Issue(models.Model):
    """Main issue/report model"""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Source(models.TextChoices):
        WEB = "web", "Web Platform"
        MOBILE = "mobile", "Mobile App"
        WHATSAPP = "whatsapp", "WhatsApp Bot"
        ECHO_AI = "echo_ai", "Echo AI"
        API = "api", "API"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.TextField(validators=[MinLengthValidator(10)])

    # Relationships
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posted_issues"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="issues"
    )
    assigned_agency = models.ForeignKey(
        GovernmentAgency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_issues",
    )

    # Metadata
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WEB)
    location = models.CharField(max_length=100)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=11, decimal_places=8, null=True, blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    agency_assigned_at = models.DateTimeField(null=True, blank=True)
    agency_response_time = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Engagement
    likes = models.ManyToManyField(User, through="Like", related_name="liked_issues")
    reposts = models.ManyToManyField(
        User, through="Repost", related_name="reposted_issues"
    )
    views_count = models.PositiveIntegerField(default=0)

    # Moderation
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)

    # WhatsApp specific fields
    whatsapp_message_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_sender_number = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["location"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"Issue #{self.issue_number}: {self.title[:50]}"

    @property
    def issue_number(self):
        """Generate a readable issue number"""
        return str(self.created_at.year) + str(self.pk).split("-")[0].upper()

    @property
    def time_ago(self):
        """Human-readable time since creation"""
        from django.utils import timezone
        from django.utils.timesince import timesince

        return timesince(self.created_at, timezone.now())

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def reposts_count(self):
        return self.reposts.count()

    @property
    def comments_count(self):
        return self.comments.filter(is_active=True).count()

    def get_absolute_url(self):
        return reverse("issue_detail", kwargs={"pk": self.pk})

    def assign_to_agency(self):
        """Auto-assign issue to appropriate agency based on category"""
        if self.category and not self.assigned_agency:
            # Find agency that handles this category
            agency = self.category.agencies.filter(is_active=True).first()
            if agency:
                self.assigned_agency = agency
                self.agency_assigned_at = timezone.now()
                self.status = self.Status.ACKNOWLEDGED
                self.save(
                    update_fields=["assigned_agency", "agency_assigned_at", "status"]
                )
                return True
        return False

    def mark_resolved(self, user=None):
        """Mark issue as resolved"""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])

        # Update author's metrics
        self.author.update_engagement_metrics()

        # Update agency metrics
        if self.assigned_agency:
            self.assigned_agency.update_metrics()


class IssueImage(models.Model):
    """Images attached to issues"""

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="issue_images/")
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "uploaded_at"]

    def __str__(self):
        return f"Image for {self.issue}"


class Comment(models.Model):
    """Comments on issues"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField(validators=[MinLengthValidator(3)])

    # For nested replies
    parent_comment = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    # Engagement on comments
    likes = models.ManyToManyField(
        User, through="CommentLike", related_name="liked_comments"
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["issue", "created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.issue}"

    @property
    def time_ago(self):
        from django.utils import timezone
        from django.utils.timesince import timesince

        return timesince(self.created_at, timezone.now())

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def replies_count(self):
        return self.replies.filter(is_active=True).count()


class AgencyResponse(models.Model):
    """Official responses from government agencies"""

    issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE, related_name="agency_responses"
    )
    agency = models.ForeignKey(GovernmentAgency, on_delete=models.CASCADE)
    responder = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"user_type__in": ["official", "agency"]},
    )
    content = models.TextField()
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Response from {self.agency} on {self.issue}"

    def save(self, *args, **kwargs):
        # Update issue's agency response time on first response
        if not self.issue.agency_response_time:
            self.issue.agency_response_time = timezone.now()
            self.issue.save(update_fields=["agency_response_time"])
        super().save(*args, **kwargs)


# Engagement Models
class Like(models.Model):
    """Likes on issues"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "issue"]


class CommentLike(models.Model):
    """Likes on comments"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "comment"]


class Repost(models.Model):
    """Reposts/shares of issues"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, help_text="Optional comment when reposting")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "issue"]


class Notification(models.Model):
    """User notifications"""

    class NotificationType(models.TextChoices):
        LIKE = "like", "Issue Liked"
        COMMENT = "comment", "New Comment"
        REPOST = "repost", "Issue Reposted"
        AGENCY_RESPONSE = "agency_response", "Agency Response"
        STATUS_UPDATE = "status_update", "Status Updated"
        WHATSAPP_REPLY = "whatsapp_reply", "WhatsApp Reply"

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices
    )
    title = models.CharField(max_length=100)
    message = models.TextField()

    # Optional references
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, null=True, blank=True
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"


class WhatsAppMessage(models.Model):
    """WhatsApp integration tracking"""

    class MessageType(models.TextChoices):
        INCOMING = "incoming", "Incoming"
        OUTGOING = "outgoing", "Outgoing"

    message_id = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=15)
    message_type = models.CharField(max_length=10, choices=MessageType.choices)
    content = models.TextField()

    # Link to user if they exist
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Link to created issue if this message created one
    created_issue = models.ForeignKey(
        Issue, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"WhatsApp message from {self.phone_number}"


class TrendingTopic(models.Model):
    """Trending hashtags and topics"""

    tag = models.CharField(max_length=50, unique=True)
    count = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-count", "-last_updated"]

    def __str__(self):
        return f"{self.tag} ({self.count} mentions)"
