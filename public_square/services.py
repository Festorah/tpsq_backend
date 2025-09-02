# services.py - Business Logic Layer

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, F, Q
from django.template.loader import render_to_string
from django.utils import timezone

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


class IssueService:
    """Service for handling issue-related business logic"""

    @staticmethod
    def create_issue(
        author: User,
        title: str,
        content: str,
        category_slug: str,
        location: str,
        source: str = "web",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        images: List = None,
        whatsapp_data: Optional[Dict] = None,
    ) -> Issue:
        """Create a new issue with all associated logic"""

        with transaction.atomic():
            # Get category
            try:
                category = Category.objects.get(slug=category_slug, is_active=True)
            except Category.DoesNotExist:
                category = None

            # Create issue
            issue = Issue.objects.create(
                title=title,
                content=content,
                author=author,
                category=category,
                location=location,
                source=source,
                latitude=latitude,
                longitude=longitude,
                whatsapp_message_id=(
                    whatsapp_data.get("message_id") if whatsapp_data else None
                ),
                whatsapp_sender_number=(
                    whatsapp_data.get("phone_number") if whatsapp_data else None
                ),
            )

            # Handle images
            if images:
                for i, image in enumerate(images):
                    IssueImage.objects.create(
                        issue=issue, image=image, is_primary=(i == 0)
                    )

            # Auto-assign to agency
            issue.assign_to_agency()

            # Update author metrics
            author.update_engagement_metrics()

            # Extract and create trending topics
            TrendingService.extract_and_update_trends(content, location)

            # Send notifications to relevant parties
            NotificationService.notify_issue_created(issue)

            return issue

    @staticmethod
    def get_filtered_issues(
        user: Optional[User] = None,
        filter_type: str = "all",
        category: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        page_size: int = 20,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Get filtered issues based on criteria"""

        queryset = (
            Issue.objects.select_related("author", "category", "assigned_agency")
            .prefetch_related("likes", "reposts", "comments", "images")
            .filter(is_active=True)
        )

        # Apply filters
        if filter_type == "trending":
            # Issues with high engagement in last 24 hours
            yesterday = timezone.now() - timedelta(days=1)
            queryset = (
                queryset.annotate(
                    engagement_score=Count("likes")
                    + Count("reposts")
                    + Count("comments")
                )
                .filter(created_at__gte=yesterday)
                .order_by("-engagement_score", "-created_at")
            )

        elif filter_type == "nearby" and user and user.location:
            queryset = queryset.filter(location__icontains=user.location)

        elif filter_type == "resolved":
            queryset = queryset.filter(status="resolved")

        elif filter_type == "following" and user:
            # Issues user has engaged with
            queryset = queryset.filter(
                Q(likes=user) | Q(reposts=user) | Q(comments__author=user)
            ).distinct()

        # Additional filters
        if category:
            queryset = queryset.filter(category__slug=category)

        if location:
            queryset = queryset.filter(location__icontains=location)

        if status:
            queryset = queryset.filter(status=status)

        # Default ordering
        if filter_type != "trending":
            queryset = queryset.order_by("-created_at")

        # Pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        issues = list(queryset[start:end])

        return {
            "issues": issues,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "has_next": end < total_count,
            "has_prev": page > 1,
        }

    @staticmethod
    def toggle_like(issue: Issue, user: User) -> Dict[str, Any]:
        """Toggle like on an issue"""

        like, created = Like.objects.get_or_create(user=user, issue=issue)

        if not created:
            like.delete()
            action = "unliked"
        else:
            action = "liked"
            # Create notification for issue author
            if issue.author != user:
                NotificationService.create_notification(
                    recipient=issue.author,
                    notification_type="like",
                    title=f"{user.full_name} liked your issue",
                    message=f'Your issue "{issue.title}" received a like',
                    issue=issue,
                )

        return {
            "action": action,
            "likes_count": issue.likes_count,
            "user_liked": action == "liked",
        }

    @staticmethod
    def toggle_repost(issue: Issue, user: User, comment: str = "") -> Dict[str, Any]:
        """Toggle repost on an issue"""

        repost, created = Repost.objects.get_or_create(
            user=user, issue=issue, defaults={"comment": comment}
        )

        if not created:
            repost.delete()
            action = "unreposted"
        else:
            action = "reposted"
            # Create notification for issue author
            if issue.author != user:
                NotificationService.create_notification(
                    recipient=issue.author,
                    notification_type="repost",
                    title=f"{user.full_name} reposted your issue",
                    message=f'Your issue "{issue.title}" was reposted',
                    issue=issue,
                )

        return {
            "action": action,
            "reposts_count": issue.reposts_count,
            "user_reposted": action == "reposted",
        }


class CommentService:
    """Service for handling comment-related business logic"""

    @staticmethod
    def create_comment(
        issue: Issue,
        author: User,
        content: str,
        parent_comment: Optional[Comment] = None,
    ) -> Comment:
        """Create a new comment"""

        with transaction.atomic():
            comment = Comment.objects.create(
                issue=issue,
                author=author,
                content=content,
                parent_comment=parent_comment,
            )

            # Create notification for issue author
            if issue.author != author:
                NotificationService.create_notification(
                    recipient=issue.author,
                    notification_type="comment",
                    title=f"New comment on your issue",
                    message=f'{author.full_name} commented: "{content[:50]}..."',
                    issue=issue,
                    comment=comment,
                )

            # Update author engagement
            author.update_engagement_metrics()

            return comment

    @staticmethod
    def get_issue_comments(issue: Issue, include_replies: bool = True) -> List[Comment]:
        """Get all comments for an issue"""

        queryset = Comment.objects.select_related("author").filter(
            issue=issue, is_active=True
        )

        if not include_replies:
            queryset = queryset.filter(parent_comment__isnull=True)

        return list(queryset.order_by("created_at"))

    @staticmethod
    def toggle_comment_like(comment: Comment, user: User) -> Dict[str, Any]:
        """Toggle like on a comment"""

        from .models import CommentLike

        like, created = CommentLike.objects.get_or_create(user=user, comment=comment)

        if not created:
            like.delete()
            action = "unliked"
        else:
            action = "liked"

        return {
            "action": action,
            "likes_count": comment.likes_count,
            "user_liked": action == "liked",
        }


class WhatsAppService:
    """Service for WhatsApp integration"""

    WHATSAPP_API_URL = getattr(settings, "WHATSAPP_API_URL", "")
    ACCESS_TOKEN = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
    VERIFY_TOKEN = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "")
    PHONE_NUMBER_ID = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")

    @classmethod
    def verify_webhook(cls, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify WhatsApp webhook"""
        if mode == "subscribe" and token == cls.VERIFY_TOKEN:
            return challenge
        return None

    @classmethod
    def process_incoming_message(cls, webhook_data: Dict) -> Dict[str, Any]:
        """Process incoming WhatsApp message"""

        try:
            entry = webhook_data["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]

            if "messages" not in value:
                return {"status": "no_messages", "message": "No messages to process"}

            messages = value["messages"]
            contacts = value.get("contacts", [])

            results = []

            for message in messages:
                result = cls._process_single_message(message, contacts)
                results.append(result)

            return {
                "status": "success",
                "processed_count": len(results),
                "results": results,
            }

        except Exception as e:
            return {"status": "error", "message": f"Error processing message: {str(e)}"}

    @classmethod
    def _process_single_message(cls, message: Dict, contacts: List) -> Dict:
        """Process a single WhatsApp message"""

        message_id = message["id"]
        from_number = message["from"]
        timestamp = message["timestamp"]
        message_type = message["type"]

        # Save message to database
        whatsapp_msg, created = WhatsAppMessage.objects.get_or_create(
            message_id=message_id,
            defaults={
                "phone_number": from_number,
                "message_type": "incoming",
                "content": "",
                "created_at": datetime.fromtimestamp(int(timestamp)),
            },
        )

        if not created:
            return {"status": "duplicate", "message_id": message_id}

        try:
            # Extract message content based on type
            if message_type == "text":
                content = message["text"]["body"]
            elif message_type == "image":
                content = message.get("image", {}).get("caption", "Image shared")
            else:
                content = f"Unsupported message type: {message_type}"

            whatsapp_msg.content = content
            whatsapp_msg.save()

            # Try to find or create user
            user = cls._find_or_create_user_from_whatsapp(from_number, contacts)
            whatsapp_msg.user = user
            whatsapp_msg.save()

            # Process as issue if it looks like a report
            if cls._is_issue_report(content):
                issue = cls._create_issue_from_whatsapp(content, user, whatsapp_msg)
                whatsapp_msg.created_issue = issue
                whatsapp_msg.is_processed = True
                whatsapp_msg.save()

                # Send confirmation
                cls._send_confirmation_message(from_number, issue)

                return {
                    "status": "issue_created",
                    "message_id": message_id,
                    "issue_id": str(issue.id),
                }
            else:
                # Send help message
                cls._send_help_message(from_number)
                return {"status": "help_sent", "message_id": message_id}

        except Exception as e:
            whatsapp_msg.processing_error = str(e)
            whatsapp_msg.save()
            return {"status": "error", "message_id": message_id, "error": str(e)}

    @classmethod
    def _find_or_create_user_from_whatsapp(
        cls, phone_number: str, contacts: List
    ) -> User:
        """Find or create user from WhatsApp contact info"""

        # Try to find existing user by phone
        try:
            return User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            pass

        # Create new user
        contact_name = "WhatsApp User"
        for contact in contacts:
            if contact["wa_id"] == phone_number:
                contact_name = contact.get("profile", {}).get("name", contact_name)
                break

        # Generate username
        username = f"whatsapp_{phone_number[-8:]}"
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1

        user = User.objects.create(
            username=username,
            first_name=contact_name,
            phone_number=phone_number,
            user_type="citizen",
        )

        return user

    @classmethod
    def _is_issue_report(cls, content: str) -> bool:
        """Determine if message content is an issue report"""

        # Keywords that indicate an issue report
        issue_keywords = [
            "problem",
            "issue",
            "broken",
            "not working",
            "damage",
            "repair",
            "water",
            "electricity",
            "road",
            "pothole",
            "trash",
            "garbage",
            "security",
            "crime",
            "emergency",
            "help",
            "complaint",
            "report",
        ]

        content_lower = content.lower()
        return any(keyword in content_lower for keyword in issue_keywords)

    @classmethod
    def _create_issue_from_whatsapp(
        cls, content: str, user: User, whatsapp_msg: WhatsAppMessage
    ) -> Issue:
        """Create issue from WhatsApp message"""

        # Extract location if mentioned
        location = cls._extract_location(content)

        # Auto-categorize based on content
        category = cls._auto_categorize_content(content)

        # Generate title from content
        title = cls._generate_title_from_content(content)

        return IssueService.create_issue(
            author=user,
            title=title,
            content=content,
            category_slug=category.slug if category else None,
            location=location or user.location or "FCT",
            source="whatsapp",
            whatsapp_data={
                "message_id": whatsapp_msg.message_id,
                "phone_number": whatsapp_msg.phone_number,
            },
        )

    @classmethod
    def _extract_location(cls, content: str) -> Optional[str]:
        """Extract location from message content"""

        # Common FCT locations
        fct_locations = [
            "Kubwa",
            "Gwarinpa",
            "Garki",
            "Wuse",
            "Maitama",
            "Asokoro",
            "Utako",
            "Jabi",
            "Life Camp",
            "Karu",
            "Nyanya",
            "Gwagwalada",
            "Airport Road",
            "Ahmadu Bello Way",
            "Constitution Avenue",
        ]

        content_lower = content.lower()
        for location in fct_locations:
            if location.lower() in content_lower:
                return location

        return None

    @classmethod
    def _auto_categorize_content(cls, content: str) -> Optional[Category]:
        """Auto-categorize content based on keywords"""

        category_keywords = {
            "water": ["water", "pipe", "burst", "leak", "borehole", "tap"],
            "electricity": [
                "light",
                "power",
                "electricity",
                "transformer",
                "cable",
                "outage",
            ],
            "roads": ["road", "pothole", "traffic", "bridge", "street"],
            "security": ["security", "crime", "robbery", "theft", "police"],
            "healthcare": ["hospital", "clinic", "health", "medical", "doctor"],
            "environment": ["waste", "garbage", "trash", "cleaning", "pollution"],
        }

        content_lower = content.lower()

        for category_slug, keywords in category_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                try:
                    return Category.objects.get(slug=category_slug, is_active=True)
                except Category.DoesNotExist:
                    continue

        return None

    @classmethod
    def _generate_title_from_content(cls, content: str) -> str:
        """Generate a title from message content"""

        # Take first sentence or first 100 characters
        sentences = content.split(".")
        if len(sentences[0]) <= 100:
            return sentences[0].strip()

        return content[:100].strip() + "..."

    @classmethod
    def send_message(cls, to_number: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp message"""

        if not cls.ACCESS_TOKEN or not cls.PHONE_NUMBER_ID:
            return {"status": "error", "message": "WhatsApp not configured"}

        url = f"{cls.WHATSAPP_API_URL}/{cls.PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {cls.ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            return {
                "status": "success",
                "message_id": response.json().get("messages", [{}])[0].get("id"),
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @classmethod
    def _send_confirmation_message(cls, to_number: str, issue: Issue):
        """Send confirmation message after issue creation"""

        message = f"""✅ Issue Reported Successfully!

Your issue has been registered with ID: #{issue.issue_number}

*Summary:* {issue.title}
*Category:* {issue.category.name if issue.category else 'General'}
*Location:* {issue.location}
*Status:* {issue.get_status_display()}

{f'*Assigned to:* {issue.assigned_agency.name}' if issue.assigned_agency else ''}

You can track your issue online at: {settings.FRONTEND_URL}/issues/{issue.id}

Thank you for helping improve FCT! 🏛️"""

        cls.send_message(to_number, message)

    @classmethod
    def _send_help_message(cls, to_number: str):
        """Send help message for unrecognized content"""

        message = """🏛️ Welcome to The Public Square - FCT Issue Reporting

To report an issue, send a message describing:
• The problem you're experiencing
• Location where it's happening
• Any other relevant details

*Examples:*
- "Water pipe burst on Kubwa Main Road, causing flooding"
- "Street lights not working in Gwarinpa Estate"
- "Pothole on Airport Road damaging cars"

Your reports help make FCT better! 🇳🇬"""

        cls.send_message(to_number, message)


class NotificationService:
    """Service for handling notifications"""

    @staticmethod
    def create_notification(
        recipient: User,
        notification_type: str,
        title: str,
        message: str,
        issue: Optional[Issue] = None,
        comment: Optional[Comment] = None,
    ) -> Notification:
        """Create a notification"""

        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            issue=issue,
            comment=comment,
        )

    @staticmethod
    def notify_issue_created(issue: Issue):
        """Send notifications when an issue is created"""

        # Notify assigned agency
        if issue.assigned_agency:
            agency_users = User.objects.filter(
                user_type__in=["official", "agency"], is_active=True
            )

            for user in agency_users:
                NotificationService.create_notification(
                    recipient=user,
                    notification_type="status_update",
                    title="New Issue Assigned",
                    message=f'New issue "{issue.title}" has been assigned to your agency',
                    issue=issue,
                )

    @staticmethod
    def get_user_notifications(
        user: User, unread_only: bool = False
    ) -> List[Notification]:
        """Get user's notifications"""

        queryset = user.notifications.select_related("issue", "comment")

        if unread_only:
            queryset = queryset.filter(is_read=False)

        return list(queryset[:20])  # Limit to recent 20

    @staticmethod
    def mark_as_read(notification: Notification):
        """Mark notification as read"""
        notification.is_read = True
        notification.save(update_fields=["is_read"])


class TrendingService:
    """Service for handling trending topics"""

    @staticmethod
    def extract_and_update_trends(content: str, location: str):
        """Extract hashtags and update trending topics"""

        # Extract hashtags
        hashtags = re.findall(r"#\w+", content.lower())

        for hashtag in hashtags:
            trend, created = TrendingTopic.objects.get_or_create(
                tag=hashtag, location=location, defaults={"count": 0}
            )
            trend.count = F("count") + 1
            trend.save(update_fields=["count"])

    @staticmethod
    def get_trending_topics(location: str = "", limit: int = 10) -> List[TrendingTopic]:
        """Get trending topics"""

        queryset = TrendingTopic.objects.filter(is_active=True)

        if location:
            queryset = queryset.filter(location__icontains=location)

        return list(queryset.order_by("-count", "-last_updated")[:limit])


class AnalyticsService:
    """Service for analytics and metrics"""

    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """Get dashboard statistics"""

        today = timezone.now().date()

        return {
            "today_stats": {
                "new_issues": Issue.objects.filter(created_at__date=today).count(),
                "in_progress": Issue.objects.filter(status="in_progress").count(),
                "resolved_today": Issue.objects.filter(resolved_at__date=today).count(),
                "active_users": User.objects.filter(
                    last_login__date=today, is_active=True
                ).count(),
            },
            "echo_ai_stats": {
                "issues_found_today": Issue.objects.filter(
                    source="echo_ai", created_at__date=today
                ).count(),
                "social_mentions": 156,  # This would come from social media monitoring
                "auto_categorized_rate": 98,
            },
            "category_breakdown": list(
                Category.objects.annotate(
                    issue_count=Count("issues", filter=Q(issues__is_active=True))
                ).values("name", "issue_count", "icon_class")
            ),
        }
