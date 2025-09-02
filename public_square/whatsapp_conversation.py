# Enhanced WhatsApp Service with Conversation Flow

import json
import re
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from .models import Category, Issue, User, WhatsAppMessage


class WhatsAppConversationService:
    """Enhanced WhatsApp service with conversation management"""

    # Conversation states
    STATE_GREETING = "greeting"
    STATE_WAITING_ISSUE = "waiting_issue"
    STATE_WAITING_LOCATION = "waiting_location"
    STATE_WAITING_CATEGORY = "waiting_category"
    STATE_CONFIRMATION = "confirmation"
    STATE_COMPLETE = "complete"

    @classmethod
    def process_incoming_message(cls, webhook_data: Dict) -> Dict[str, Any]:
        """Enhanced message processing with conversation flow"""

        try:
            entry = webhook_data["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]

            if "messages" not in value:
                return {"status": "no_messages"}

            messages = value["messages"]
            contacts = value.get("contacts", [])

            results = []

            for message in messages:
                result = cls._process_single_message_with_flow(message, contacts)
                results.append(result)

            return {
                "status": "success",
                "processed_count": len(results),
                "results": results,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    @classmethod
    def _process_single_message_with_flow(cls, message: Dict, contacts: List) -> Dict:
        """Process message with conversation flow"""

        message_id = message["id"]
        from_number = message["from"]
        message_type = message["type"]

        # Extract message content
        if message_type == "text":
            content = message["text"]["body"].strip()
        elif message_type == "interactive":
            # Handle button/list replies
            if "button_reply" in message["interactive"]:
                content = message["interactive"]["button_reply"]["id"]
            elif "list_reply" in message["interactive"]:
                content = message["interactive"]["list_reply"]["id"]
            else:
                content = "interactive_message"
        else:
            content = f"[{message_type}_message]"

        # Save message to database
        whatsapp_msg, created = WhatsAppMessage.objects.get_or_create(
            message_id=message_id,
            defaults={
                "phone_number": from_number,
                "message_type": "incoming",
                "content": content,
            },
        )

        if not created:
            return {"status": "duplicate", "message_id": message_id}

        try:
            # Find or create user
            user = cls._find_or_create_user_from_whatsapp(from_number, contacts)
            whatsapp_msg.user = user
            whatsapp_msg.save()

            # Get current conversation state
            conversation_state = cls._get_conversation_state(from_number)

            # Process based on conversation state
            if conversation_state == cls.STATE_GREETING or cls._is_greeting(content):
                return cls._handle_greeting(from_number, user)

            elif conversation_state == cls.STATE_WAITING_ISSUE:
                if cls._is_issue_report(content):
                    return cls._handle_issue_description(from_number, content, user)
                else:
                    return cls._handle_invalid_issue(from_number)

            elif conversation_state == cls.STATE_WAITING_LOCATION:
                return cls._handle_location_input(from_number, content, user)

            elif conversation_state == cls.STATE_WAITING_CATEGORY:
                return cls._handle_category_selection(from_number, content, user)

            elif conversation_state == cls.STATE_CONFIRMATION:
                return cls._handle_confirmation(from_number, content, user)

            else:
                # Default: Check if it's a direct issue report or greeting
                if cls._is_issue_report(content):
                    return cls._handle_direct_issue_report(
                        from_number, content, user, whatsapp_msg
                    )
                else:
                    return cls._handle_greeting(from_number, user)

        except Exception as e:
            whatsapp_msg.processing_error = str(e)
            whatsapp_msg.save()
            return {"status": "error", "message_id": message_id, "error": str(e)}

    @classmethod
    def _is_greeting(cls, content: str) -> bool:
        """Check if message is a greeting"""
        greetings = [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "hola",
            "start",
            "begin",
            "help",
            "info",
        ]
        return content.lower().strip() in greetings

    @classmethod
    def _handle_greeting(cls, phone_number: str, user: User) -> Dict:
        """Handle greeting message with welcome and options"""

        welcome_message = f"""🏛️ *Welcome to The Public Square FCT*

Hello {user.first_name}! I'm here to help you report civic issues in the Federal Capital Territory.

*Here's how it works:*
1️⃣ Describe your issue in detail
2️⃣ Provide the location  
3️⃣ I'll help categorize it
4️⃣ Get a tracking number

*You can report issues like:*
• Water supply problems
• Road damage or potholes
• Power outages
• Waste management issues
• Security concerns
• Healthcare access problems

*To get started, please describe the issue you'd like to report.*

Type your issue description now, or reply *"examples"* to see sample reports."""

        # Set conversation state
        cls._set_conversation_state(phone_number, cls.STATE_WAITING_ISSUE)

        # Send welcome message with interactive buttons
        cls._send_interactive_welcome(phone_number)

        return {
            "status": "greeting_sent",
            "phone_number": phone_number,
            "next_state": cls.STATE_WAITING_ISSUE,
        }

    @classmethod
    def _send_interactive_welcome(cls, phone_number: str):
        """Send interactive welcome message with buttons"""

        message_data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": "🏛️ *Welcome to FCT Public Square*\n\nReport civic issues and track their resolution. How would you like to proceed?"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": "report_new", "title": "Report New Issue"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": "see_examples", "title": "See Examples"},
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "track_issue",
                                "title": "Track Existing Issue",
                            },
                        },
                    ]
                },
            },
        }

        cls._send_whatsapp_message(message_data)

    @classmethod
    def _handle_issue_description(
        cls, phone_number: str, content: str, user: User
    ) -> Dict:
        """Handle issue description input"""

        # Store issue description temporarily
        cls._store_temp_data(phone_number, "issue_description", content)

        # Ask for location
        location_message = """📍 *Great! Now please provide the location.*

Where exactly is this issue occurring?

*Examples:*
• "Kubwa Phase 2, near Unity Bank"
• "Airport Road, opposite Shoprite"
• "Gwarinpa Estate, Block 5"
• "Garki Area 7, behind NNPC Towers"

Please be as specific as possible to help our response teams locate the issue quickly."""

        cls.send_message(phone_number, location_message)
        cls._set_conversation_state(phone_number, cls.STATE_WAITING_LOCATION)

        return {
            "status": "location_requested",
            "phone_number": phone_number,
            "next_state": cls.STATE_WAITING_LOCATION,
        }

    @classmethod
    def _handle_location_input(
        cls, phone_number: str, location: str, user: User
    ) -> Dict:
        """Handle location input"""

        # Store location temporarily
        cls._store_temp_data(phone_number, "location", location)

        # Send category selection
        cls._send_category_selection(phone_number)
        cls._set_conversation_state(phone_number, cls.STATE_WAITING_CATEGORY)

        return {
            "status": "category_selection_sent",
            "phone_number": phone_number,
            "next_state": cls.STATE_WAITING_CATEGORY,
        }

    @classmethod
    def _send_category_selection(cls, phone_number: str):
        """Send category selection menu"""

        message_data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": "🏷️ *Please select the category that best describes your issue:*"
                },
                "action": {
                    "button": "Select Category",
                    "sections": [
                        {
                            "title": "Infrastructure",
                            "rows": [
                                {
                                    "id": "water",
                                    "title": "💧 Water & Sanitation",
                                    "description": "Pipe bursts, water shortage, drainage",
                                },
                                {
                                    "id": "roads",
                                    "title": "🛣️ Roads & Transport",
                                    "description": "Potholes, traffic lights, bridges",
                                },
                                {
                                    "id": "electricity",
                                    "title": "⚡ Electricity",
                                    "description": "Power outages, faulty equipment",
                                },
                            ],
                        },
                        {
                            "title": "Public Services",
                            "rows": [
                                {
                                    "id": "healthcare",
                                    "title": "🏥 Healthcare",
                                    "description": "Hospital services, medical facilities",
                                },
                                {
                                    "id": "security",
                                    "title": "🛡️ Security",
                                    "description": "Safety concerns, crime reports",
                                },
                                {
                                    "id": "environment",
                                    "title": "🌱 Environment",
                                    "description": "Waste management, pollution",
                                },
                            ],
                        },
                    ],
                },
            },
        }

        cls._send_whatsapp_message(message_data)

    @classmethod
    def _handle_category_selection(
        cls, phone_number: str, category_id: str, user: User
    ) -> Dict:
        """Handle category selection"""

        # Store category temporarily
        cls._store_temp_data(phone_number, "category", category_id)

        # Get stored data
        temp_data = cls._get_temp_data(phone_number)
        issue_description = temp_data.get("issue_description", "")
        location = temp_data.get("location", "")

        # Get category name
        try:
            from .models import Category

            category = Category.objects.get(slug=category_id)
            category_name = category.name
        except Category.DoesNotExist:
            category_name = category_id.title()

        # Send confirmation
        confirmation_message = f"""📋 *Please confirm your issue report:*

*Issue Description:*
{issue_description}

*Location:*
{location}

*Category:*
{category_name}

*Reporter:*
{user.full_name}

Is this information correct?"""

        confirmation_data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": confirmation_message},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": "confirm_yes", "title": "✅ Yes, Submit"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": "confirm_no", "title": "❌ No, Start Over"},
                        },
                    ]
                },
            },
        }

        cls._send_whatsapp_message(confirmation_data)
        cls._set_conversation_state(phone_number, cls.STATE_CONFIRMATION)

        return {
            "status": "confirmation_sent",
            "phone_number": phone_number,
            "next_state": cls.STATE_CONFIRMATION,
        }

    @classmethod
    def _handle_confirmation(cls, phone_number: str, response: str, user: User) -> Dict:
        """Handle confirmation response"""

        if response == "confirm_yes":
            # Create the issue
            temp_data = cls._get_temp_data(phone_number)

            try:
                from .services import IssueService

                issue = IssueService.create_issue(
                    author=user,
                    title=temp_data["issue_description"][:100] + "...",
                    content=temp_data["issue_description"],
                    category_slug=temp_data["category"],
                    location=temp_data["location"],
                    source="whatsapp",
                    whatsapp_data={"phone_number": phone_number},
                )

                # Send success confirmation
                success_message = f"""✅ *Issue Successfully Reported!*

*Issue ID:* #{issue.issue_number}
*Status:* {issue.get_status_display()}
*Category:* {issue.category.name if issue.category else 'General'}
*Location:* {issue.location}

{f"*Assigned to:* {issue.assigned_agency.name}" if issue.assigned_agency else "*Status:* Under review"}

🔗 *Track online:* {settings.FRONTEND_URL}/issues/{issue.id}

*What happens next?*
1️⃣ Your issue will be reviewed within 24 hours
2️⃣ The relevant agency will be notified
3️⃣ You'll receive updates on progress
4️⃣ Track resolution on our website

Thank you for helping improve FCT! 🇳🇬

_Reply *"new"* to report another issue or *"track [Issue ID]"* to check status._"""

                cls.send_message(phone_number, success_message)

                # Clear temporary data
                cls._clear_temp_data(phone_number)
                cls._set_conversation_state(phone_number, cls.STATE_COMPLETE)

                return {
                    "status": "issue_created",
                    "phone_number": phone_number,
                    "issue_id": str(issue.id),
                    "issue_number": issue.issue_number,
                }

            except Exception as e:
                error_message = """❌ *Error creating your issue report.*

Please try again or visit our website directly. If the problem persists, contact our support team.

Reply *"start"* to try again."""

                cls.send_message(phone_number, error_message)
                return {"status": "creation_error", "error": str(e)}

        elif response == "confirm_no":
            # Start over
            cls._clear_temp_data(phone_number)
            return cls._handle_greeting(phone_number, user)

        else:
            # Invalid response
            invalid_message = """❓ Please select one of the options:
            
✅ *Yes, Submit* - to create your issue report
❌ *No, Start Over* - to start again"""

            cls.send_message(phone_number, invalid_message)
            return {"status": "invalid_confirmation"}

    @classmethod
    def _handle_direct_issue_report(
        cls, phone_number: str, content: str, user: User, whatsapp_msg: WhatsAppMessage
    ) -> Dict:
        """Handle direct issue report (user sends issue without greeting)"""

        # Extract location if mentioned
        location = cls._extract_location(content) or user.location or "FCT"

        # Auto-categorize
        category = cls._auto_categorize_content(content)

        # Create issue directly
        try:
            from .services import IssueService

            issue = IssueService.create_issue(
                author=user,
                title=content[:100] + "..." if len(content) > 100 else content,
                content=content,
                category_slug=category.slug if category else None,
                location=location,
                source="whatsapp",
                whatsapp_data={
                    "message_id": whatsapp_msg.message_id,
                    "phone_number": phone_number,
                },
            )

            whatsapp_msg.created_issue = issue
            whatsapp_msg.is_processed = True
            whatsapp_msg.save()

            # Send confirmation
            cls._send_issue_confirmation(phone_number, issue)

            return {
                "status": "direct_issue_created",
                "phone_number": phone_number,
                "issue_id": str(issue.id),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @classmethod
    def _handle_invalid_issue(cls, phone_number: str) -> Dict:
        """Handle invalid issue description"""

        help_message = """❓ *I need more details to help you report this issue.*

Please describe the problem you're experiencing in detail. Include:

🔍 *What* is the problem?
📍 *Where* is it located?
⏰ *When* did you notice it?
🎯 *How* is it affecting you or your community?

*Example:*
"Water pipe burst on Kubwa Main Road near First Bank. Water has been flowing for 2 days and the road is flooded, making it difficult for cars to pass."

Please try describing your issue again:"""

        cls.send_message(phone_number, help_message)

        return {"status": "help_sent", "phone_number": phone_number}

    # Utility methods for conversation state management
    @classmethod
    def _get_conversation_state(cls, phone_number: str) -> str:
        """Get current conversation state for user"""
        from django.core.cache import cache

        return cache.get(f"whatsapp_state_{phone_number}", cls.STATE_GREETING)

    @classmethod
    def _set_conversation_state(cls, phone_number: str, state: str):
        """Set conversation state for user"""
        from django.core.cache import cache

        cache.set(f"whatsapp_state_{phone_number}", state, 3600)  # 1 hour timeout

    @classmethod
    def _store_temp_data(cls, phone_number: str, key: str, value: str):
        """Store temporary conversation data"""
        from django.core.cache import cache

        cache_key = f"whatsapp_temp_{phone_number}"
        temp_data = cache.get(cache_key, {})
        temp_data[key] = value
        cache.set(cache_key, temp_data, 3600)

    @classmethod
    def _get_temp_data(cls, phone_number: str) -> Dict:
        """Get temporary conversation data"""
        from django.core.cache import cache

        return cache.get(f"whatsapp_temp_{phone_number}", {})

    @classmethod
    def _clear_temp_data(cls, phone_number: str):
        """Clear temporary conversation data"""
        from django.core.cache import cache

        cache.delete(f"whatsapp_temp_{phone_number}")
        cache.delete(f"whatsapp_state_{phone_number}")

    @classmethod
    def _send_whatsapp_message(cls, message_data: Dict):
        """Send WhatsApp message using Facebook Graph API"""

        url = (
            f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, headers=headers, json=message_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            return None

    @classmethod
    def send_message(cls, to_number: str, message: str):
        """Send simple text message"""

        message_data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message},
        }

        return cls._send_whatsapp_message(message_data)

    # Inherit other methods from original WhatsAppService
    @classmethod
    def _is_issue_report(cls, content: str) -> bool:
        """Determine if message content is an issue report"""

        if len(content.strip()) < 10:  # Too short to be meaningful
            return False

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
            "flooding",
            "burst",
            "outage",
            "fault",
            "blocked",
            "overflow",
        ]

        content_lower = content.lower()
        return any(keyword in content_lower for keyword in issue_keywords)

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
    def _auto_categorize_content(cls, content: str) -> Optional:
        """Auto-categorize content based on keywords"""

        from .models import Category

        category_keywords = {
            "water": [
                "water",
                "pipe",
                "burst",
                "leak",
                "borehole",
                "tap",
                "drainage",
                "sewage",
            ],
            "electricity": [
                "light",
                "power",
                "electricity",
                "transformer",
                "cable",
                "outage",
            ],
            "roads": ["road", "pothole", "traffic", "bridge", "street", "highway"],
            "security": ["security", "crime", "robbery", "theft", "police", "safety"],
            "healthcare": [
                "hospital",
                "clinic",
                "health",
                "medical",
                "doctor",
                "ambulance",
            ],
            "environment": [
                "waste",
                "garbage",
                "trash",
                "cleaning",
                "pollution",
                "dump",
            ],
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
    def _find_or_create_user_from_whatsapp(cls, phone_number: str, contacts: List):
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

        # Split contact name into first and last name
        name_parts = contact_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            user_type="citizen",
        )

        return user

    @classmethod
    def _send_issue_confirmation(cls, to_number: str, issue):
        """Send confirmation message after issue creation"""

        message = f"""✅ *Issue Reported Successfully!*

*Issue ID:* #{issue.issue_number}
*Category:* {issue.category.name if issue.category else 'General'}
*Location:* {issue.location}
*Status:* {issue.get_status_display()}

{f'*Assigned to:* {issue.assigned_agency.name}' if issue.assigned_agency else ''}

🔗 *Track online:* {settings.FRONTEND_URL}/issues/{issue.id}

Thank you for helping improve FCT! 🏛️

_Reply *"new"* to report another issue._"""

        cls.send_message(to_number, message)
