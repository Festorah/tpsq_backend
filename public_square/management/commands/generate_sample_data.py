# management/commands/generate_sample_data.py

import os
import random
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from public_square.models import (
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
)
from public_square.services import CommentService, IssueService

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = "Generate sample data for The Public Square platform"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=50, help="Number of users to create"
        )
        parser.add_argument(
            "--issues", type=int, default=100, help="Number of issues to create"
        )
        parser.add_argument(
            "--comments", type=int, default=300, help="Number of comments to create"
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before generating new data",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            self.clear_data()

        self.stdout.write("Creating categories and agencies...")
        self.create_categories_and_agencies()

        self.stdout.write(f"Creating {options['users']} users...")
        self.create_users(options["users"])

        self.stdout.write(f"Creating {options['issues']} issues...")
        self.create_issues(options["issues"])

        self.stdout.write(f"Creating {options['comments']} comments...")
        self.create_comments(options["comments"])

        self.stdout.write("Creating engagement data...")
        self.create_engagement_data()

        self.stdout.write("Creating trending topics...")
        self.create_trending_topics()

        self.stdout.write("Creating notifications...")
        self.create_notifications()

        self.stdout.write(self.style.SUCCESS("Successfully generated sample data!"))

    def clear_data(self):
        """Clear existing data"""
        models_to_clear = [
            Notification,
            AgencyResponse,
            Comment,
            Like,
            Repost,
            IssueImage,
            Issue,
            TrendingTopic,
            GovernmentAgency,
            Category,
        ]

        for model in models_to_clear:
            model.objects.all().delete()

        # Keep superuser, delete other users
        User.objects.filter(is_superuser=False).delete()

    def create_categories_and_agencies(self):
        """Create categories and government agencies"""

        categories_data = [
            {
                "name": "Water & Sanitation",
                "slug": "water",
                "description": "Water supply, drainage, and sanitation issues",
                "icon_class": "fas fa-tint",
                "color": "#3b82f6",
            },
            {
                "name": "Roads & Infrastructure",
                "slug": "roads",
                "description": "Road conditions, potholes, bridges, and transportation",
                "icon_class": "fas fa-road",
                "color": "#6b7280",
            },
            {
                "name": "Electricity",
                "slug": "electricity",
                "description": "Power outages, electrical faults, and energy issues",
                "icon_class": "fas fa-bolt",
                "color": "#f59e0b",
            },
            {
                "name": "Healthcare",
                "slug": "healthcare",
                "description": "Healthcare facilities, medical services, and public health",
                "icon_class": "fas fa-heartbeat",
                "color": "#ef4444",
            },
            {
                "name": "Security",
                "slug": "security",
                "description": "Safety, crime prevention, and emergency services",
                "icon_class": "fas fa-shield-alt",
                "color": "#dc2626",
            },
            {
                "name": "Environment",
                "slug": "environment",
                "description": "Waste management, pollution, and environmental protection",
                "icon_class": "fas fa-leaf",
                "color": "#10b981",
            },
            {
                "name": "Education",
                "slug": "education",
                "description": "Schools, educational facilities, and learning resources",
                "icon_class": "fas fa-graduation-cap",
                "color": "#8b5cf6",
            },
            {
                "name": "Welfare",
                "slug": "welfare",
                "description": "Social services, pensions, and citizen welfare",
                "icon_class": "fas fa-hands-helping",
                "color": "#06b6d4",
            },
        ]

        categories = []
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data["slug"], defaults=cat_data
            )
            categories.append(category)

        # Create government agencies
        agencies_data = [
            {
                "name": "FCT Water Board",
                "abbreviation": "FCTWB",
                "description": "Manages water supply and sanitation in FCT",
                "contact_email": "info@fctwaterboard.gov.ng",
                "contact_phone": "+2349012345678",
                "website": "https://fctwaterboard.gov.ng",
                "categories": ["water"],
            },
            {
                "name": "FCT Engineering Services",
                "abbreviation": "FCTES",
                "description": "Handles road construction and maintenance",
                "contact_email": "info@fctengineering.gov.ng",
                "contact_phone": "+2349012345679",
                "website": "https://fctengineering.gov.ng",
                "categories": ["roads"],
            },
            {
                "name": "Abuja Electricity Distribution Company",
                "abbreviation": "AEDC",
                "description": "Power distribution in FCT",
                "contact_email": "customercare@abujaelectricity.com",
                "contact_phone": "+2349012345680",
                "website": "https://abujaelectricity.com",
                "categories": ["electricity"],
            },
            {
                "name": "FCT Health and Human Services",
                "abbreviation": "FCTHHS",
                "description": "Healthcare services and facilities management",
                "contact_email": "info@fcthealth.gov.ng",
                "contact_phone": "+2349012345681",
                "website": "https://fcthealth.gov.ng",
                "categories": ["healthcare"],
            },
            {
                "name": "FCT Security Services",
                "abbreviation": "FCTSS",
                "description": "Security coordination and emergency response",
                "contact_email": "emergency@fctsecurity.gov.ng",
                "contact_phone": "+2349012345682",
                "website": "https://fctsecurity.gov.ng",
                "categories": ["security"],
            },
            {
                "name": "Abuja Environmental Protection Board",
                "abbreviation": "AEPB",
                "description": "Environmental protection and waste management",
                "contact_email": "info@aepb.gov.ng",
                "contact_phone": "+2349012345683",
                "website": "https://aepb.gov.ng",
                "categories": ["environment"],
            },
            {
                "name": "FCT Education Secretariat",
                "abbreviation": "FCTES",
                "description": "Education policy and school management",
                "contact_email": "info@fcteducation.gov.ng",
                "contact_phone": "+2349012345684",
                "website": "https://fcteducation.gov.ng",
                "categories": ["education"],
            },
            {
                "name": "FCT Social Development Secretariat",
                "abbreviation": "FCTSDS",
                "description": "Social services and welfare programs",
                "contact_email": "info@fctsocial.gov.ng",
                "contact_phone": "+2349012345685",
                "website": "https://fctsocial.gov.ng",
                "categories": ["welfare"],
            },
        ]

        for agency_data in agencies_data:
            category_slugs = agency_data.pop("categories")
            agency, created = GovernmentAgency.objects.get_or_create(
                abbreviation=agency_data["abbreviation"], defaults=agency_data
            )

            # Assign categories
            for slug in category_slugs:
                try:
                    category = Category.objects.get(slug=slug)
                    agency.handled_categories.add(category)
                except Category.DoesNotExist:
                    pass

    def create_users(self, count):
        """Create sample users"""

        nigerian_names = [
            ("Adaora", "Okechukwu"),
            ("Emeka", "Okafor"),
            ("Fatima", "Hassan"),
            ("Ibrahim", "Sule"),
            ("Chioma", "Okafor"),
            ("Musa", "Ibrahim"),
            ("Blessing", "Eze"),
            ("Ahmed", "Suleiman"),
            ("Sarah", "Ahmed"),
            ("David", "Okon"),
            ("Hajiya", "Khadija"),
            ("Moses", "Nwachukwu"),
            ("Aisha", "Bello"),
            ("Peter", "Okafor"),
            ("Zainab", "Yusuf"),
            ("James", "Ochi"),
            ("Amina", "Garba"),
            ("John", "Ekpenyong"),
            ("Ngozi", "Udoh"),
            ("Aliyu", "Mahmud"),
        ]

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
            "Lugbe",
            "Airport Road",
            "CBD",
            "Lokogoma",
            "Durumi",
            "Kaura",
        ]

        user_types = ["citizen"] * 85 + ["official"] * 10 + ["agency"] * 5

        users = []
        for i in range(count):
            first_name, last_name = random.choice(nigerian_names)
            location = random.choice(fct_locations)
            user_type = random.choice(user_types)

            username = f"{first_name.lower()}{last_name.lower()}{i}"
            email = f"{username}@example.com"

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=f"+234{random.randint(7000000000, 9099999999)}",
                location=location,
                user_type=user_type,
                bio=fake.text(max_nb_chars=200),
                is_verified=(
                    random.choice([True, False]) if user_type != "citizen" else False
                ),
            )
            users.append(user)

        self.stdout.write(f"Created {len(users)} users")

    def create_issues(self, count):
        """Create sample issues with varied timestamps"""

        users = list(User.objects.all())
        categories = list(Category.objects.all())

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
            "Lugbe",
            "Airport Road",
            "CBD",
            "Lokogoma",
            "Durumi",
            "Kaura",
        ]

        # Issue templates by category
        issue_templates = {
            "water": [
                "Water pipe burst on {location} causing massive flooding. Residents have been without water for {days} days.",
                "Borehole not working in {location} community. Over 200 families affected by water shortage.",
                "Sewage overflow on {location} street creating health hazard and bad smell in the neighborhood.",
                "Water treatment plant malfunction causing dirty water supply to {location} area.",
                "Multiple water leaks reported along {location} main road, causing waste and road damage.",
            ],
            "roads": [
                "Major pothole on {location} road causing vehicle damage and near accidents daily.",
                "Bridge on {location} road has structural damage and needs urgent repair for safety.",
                "Street lights not working on {location} making it dangerous to drive at night.",
                "Road construction in {location} abandoned for months, creating traffic nightmare.",
                "Drainage system blocked on {location} causing flooding during rainy season.",
            ],
            "electricity": [
                "Power outage in {location} for {days} days affecting businesses and residents.",
                "Electric transformer explosion in {location} leaving entire community in darkness.",
                "Dangerous exposed electrical cables on {location} posing risk to pedestrians and drivers.",
                "Frequent power surges in {location} damaging electrical appliances in homes and offices.",
                "Street lighting system completely down in {location} increasing security concerns.",
            ],
            "healthcare": [
                "General hospital in {location} lacks essential medical equipment and supplies.",
                "Long queues and poor service at {location} primary healthcare center.",
                "Ambulance service not available in {location} during medical emergencies.",
                "Shortage of qualified medical staff at {location} health facility.",
                "Poor sanitation conditions at {location} clinic posing health risks to patients.",
            ],
            "security": [
                "Increased criminal activities in {location} area with no visible security presence.",
                "Armed robbery incidents on {location} road becoming too frequent.",
                "Poor street lighting in {location} making it unsafe for residents especially at night.",
                "Police station in {location} understaffed and poorly equipped to handle security issues.",
                "Youth restiveness in {location} community needs urgent government intervention.",
            ],
            "environment": [
                "Illegal waste dumping in {location} causing environmental pollution and health hazards.",
                "Waste collection points overflowing in {location} attracting rodents and flies.",
                "Air pollution from factory in {location} affecting residents' health and comfort.",
                "Deforestation in {location} area leading to erosion and environmental degradation.",
                "Open drainage system in {location} breeding mosquitoes and causing disease outbreaks.",
            ],
        }

        statuses = ["pending", "acknowledged", "in_progress", "resolved"]
        status_weights = [40, 30, 20, 10]  # More pending issues

        sources = ["web", "mobile", "whatsapp", "echo_ai"]
        source_weights = [50, 30, 15, 5]

        # Generate varied timestamps over the last 60 days
        now = timezone.now()
        start_date = now - timedelta(days=60)

        # Create a list of timestamps with realistic distribution
        timestamps = []

        # More issues during business hours (9 AM - 6 PM) and weekdays
        for day_offset in range(60):
            current_date = start_date + timedelta(days=day_offset)
            weekday = current_date.weekday()  # 0=Monday, 6=Sunday

            # Determine how many issues for this day (more on weekdays)
            if weekday < 5:  # Monday-Friday
                daily_issue_count = random.randint(2, 8)
            else:  # Weekend
                daily_issue_count = random.randint(1, 4)

            for _ in range(daily_issue_count):
                # Business hours (9 AM - 6 PM) get 60% of issues
                # Evening hours (6 PM - 10 PM) get 25% of issues
                # Night/early morning (10 PM - 9 AM) get 15% of issues
                hour_preference = random.random()

                if hour_preference < 0.6:  # Business hours
                    hour = random.randint(9, 17)
                elif hour_preference < 0.85:  # Evening
                    hour = random.randint(18, 21)
                else:  # Night/early morning
                    hour = random.choice(list(range(22, 24)) + list(range(0, 9)))

                minute = random.randint(0, 59)
                second = random.randint(0, 59)

                issue_time = current_date.replace(
                    hour=hour,
                    minute=minute,
                    second=second,
                    microsecond=random.randint(0, 999999),
                )
                timestamps.append(issue_time)

        # Shuffle timestamps and take only what we need
        random.shuffle(timestamps)
        timestamps = timestamps[:count]

        # Sort timestamps to make processing easier (oldest first)
        timestamps.sort()

        issues = []
        for i in range(count):
            author = random.choice(users)
            category = random.choice(categories)
            location = random.choice(fct_locations)

            # Generate content based on category
            if category.slug in issue_templates:
                template = random.choice(issue_templates[category.slug])
                days = random.randint(1, 10)
                content = template.format(location=location, days=days)
            else:
                content = fake.text(max_nb_chars=300)

            # Generate title from content
            title = content.split(".")[0][:100]
            if not title.endswith("."):
                title += "..."

            status = random.choices(statuses, weights=status_weights)[0]
            source = random.choices(sources, weights=source_weights)[0]

            # Use the pre-generated timestamp
            created_at = timestamps[i]

            issue = Issue.objects.create(
                title=title,
                content=content,
                author=author,
                category=category,
                location=location,
                status=status,
                source=source,
                created_at=created_at,
                is_urgent=(
                    random.choice([True, False]) if random.random() < 0.1 else False
                ),
                is_featured=(
                    random.choice([True, False]) if random.random() < 0.05 else False
                ),
            )

            # Assign to agency and set realistic timestamps based on status
            issue.assign_to_agency()

            if status in ["acknowledged", "in_progress", "resolved"]:
                # Agency assignment: 1-72 hours after issue creation (weighted toward faster response)
                assignment_hours = random.choices(
                    [1, 2, 4, 8, 12, 24, 48, 72], weights=[25, 20, 15, 15, 10, 8, 5, 2]
                )[0]

                issue.agency_assigned_at = created_at + timedelta(
                    hours=assignment_hours,
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                )

                # Agency response: 1-48 hours after assignment
                response_hours = random.choices(
                    [1, 2, 4, 8, 12, 24, 48], weights=[20, 18, 16, 16, 12, 10, 8]
                )[0]

                issue.agency_response_time = issue.agency_assigned_at + timedelta(
                    hours=response_hours,
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                )

            if status == "resolved":
                # Resolution: 1-14 days after first response (weighted toward faster resolution)
                resolution_days = random.choices(
                    [1, 2, 3, 5, 7, 10, 14], weights=[20, 18, 15, 15, 12, 10, 10]
                )[0]

                issue.resolved_at = issue.agency_response_time + timedelta(
                    days=resolution_days,
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                )

                # Make sure resolved_at doesn't exceed current time
                if issue.resolved_at > now:
                    issue.resolved_at = now - timedelta(
                        hours=random.randint(1, 48), minutes=random.randint(0, 59)
                    )

            issue.save()
            issues.append(issue)

            # Add some agency responses with realistic timestamps
            if issue.assigned_agency and random.random() < 0.4:
                agency_users = User.objects.filter(user_type__in=["official", "agency"])
                if agency_users.exists():
                    responder = random.choice(agency_users)
                    responses = [
                        "We have received your report and our team is investigating the issue.",
                        "Our technical team has been dispatched to assess the situation.",
                        "Thank you for reporting this. We are working on a solution.",
                        "The issue has been escalated to the relevant department for urgent action.",
                        "Repair work has been scheduled and will commence within 48 hours.",
                        "Update: Our team has identified the problem and is working on repairs.",
                        "We have allocated resources to address this issue. Expected completion in 3-5 days.",
                        "Temporary measures have been put in place while we work on a permanent solution.",
                    ]

                    # Response timestamp should be after agency_response_time
                    response_created_at = issue.agency_response_time or (
                        created_at + timedelta(hours=random.randint(2, 24))
                    )

                    # Add some variation to response time
                    response_created_at += timedelta(
                        hours=random.randint(0, 12), minutes=random.randint(0, 59)
                    )

                    AgencyResponse.objects.create(
                        issue=issue,
                        agency=issue.assigned_agency,
                        responder=responder,
                        content=random.choice(responses),
                        created_at=response_created_at,
                    )

                    # Sometimes add multiple responses for more active issues
                    if random.random() < 0.3:
                        follow_up_responses = [
                            "Update: Work is progressing as scheduled.",
                            "We have encountered some delays due to weather conditions.",
                            "Additional resources have been deployed to expedite resolution.",
                            "The issue has been partially resolved. Final checks in progress.",
                            "Quality assurance checks completed. Issue should be fully resolved.",
                        ]

                        follow_up_time = response_created_at + timedelta(
                            days=random.randint(1, 5), hours=random.randint(0, 12)
                        )

                        if follow_up_time <= now:
                            AgencyResponse.objects.create(
                                issue=issue,
                                agency=issue.assigned_agency,
                                responder=responder,
                                content=random.choice(follow_up_responses),
                                created_at=follow_up_time,
                            )

        self.stdout.write(
            f"Created {len(issues)} issues with varied timestamps spanning 60 days"
        )

    def create_comments(self, count):
        """Create sample comments with varied timestamps relative to their issues"""

        issues = list(Issue.objects.all())
        users = list(User.objects.all())

        comment_templates = [
            "I have the same problem in my area. When will this be fixed?",
            "This is affecting our daily lives. Government needs to act fast.",
            "Thank you for reporting this issue. I hope it gets resolved soon.",
            "This has been going on for too long. We need immediate action.",
            "I can confirm this problem exists. It's getting worse every day.",
            "The government should prioritize this issue. It affects many families.",
            "Has anyone heard back from the authorities about this?",
            "This is exactly what we've been experiencing. Something must be done.",
            "I hope this issue gets the attention it deserves from the government.",
            "This problem is causing serious inconvenience to residents.",
            "Update: Is there any progress on this issue?",
            "I noticed some improvement in my area. Is this being addressed?",
            "Still experiencing this problem. Any timeline for resolution?",
            "Great job reporting this! The community needs more people like you.",
            "This issue is widespread across multiple neighborhoods.",
            "Local representative should be made aware of this situation.",
            "Temporary solutions needed while permanent fix is being worked on.",
            "Has anyone tried alternative solutions in the meantime?",
            "This affects children's safety in our community.",
            "Economic impact of this issue is significant for small businesses.",
        ]

        follow_up_templates = [
            "Any updates on this issue? It's been several days now.",
            "The problem seems to be getting worse in my area.",
            "Thank you for the previous updates. When can we expect resolution?",
            "I've noticed some improvement, but the issue persists.",
            "Other communities are facing similar problems.",
            "Has anyone contacted local representatives about this?",
            "We should organize as a community to address this issue.",
        ]

        comments = []

        # Sort issues by creation time to create realistic comment patterns
        sorted_issues = sorted(issues, key=lambda x: x.created_at)

        # Create comments with realistic timing patterns
        comments_per_issue = {}

        # Distribute comments across issues (some issues get more comments)
        for issue in sorted_issues:
            # More popular/urgent issues get more comments
            base_comments = 1
            if issue.is_urgent:
                base_comments = 3
            if issue.status in ["in_progress", "resolved"]:
                base_comments += 1

            # Random variation
            num_comments = random.randint(0, base_comments + 2)
            comments_per_issue[issue.id] = min(
                num_comments, 8
            )  # Cap at 8 comments per issue

        total_comments_to_create = sum(comments_per_issue.values())
        if total_comments_to_create < count:
            # Distribute remaining comments randomly
            remaining = count - total_comments_to_create
            for _ in range(remaining):
                random_issue = random.choice(sorted_issues)
                comments_per_issue[random_issue.id] += 1

        now = timezone.now()

        for issue in sorted_issues:
            num_comments = comments_per_issue.get(issue.id, 0)
            if num_comments == 0:
                continue

            # Comments should be posted after the issue creation
            issue_age = now - issue.created_at

            for i in range(num_comments):
                author = random.choice(users)

                # Early comments (within first 24 hours)
                if i < num_comments // 2:
                    content = random.choice(
                        comment_templates[:12]
                    )  # Initial reaction comments

                    # Comments appear within hours to days after issue creation
                    comment_delay_hours = random.choices(
                        [1, 2, 4, 8, 12, 24, 48, 72],
                        weights=[20, 18, 15, 15, 12, 10, 8, 2],
                    )[0]

                    # Make sure comment time doesn't exceed current time
                    max_delay_hours = min(
                        comment_delay_hours, issue_age.total_seconds() // 3600
                    )
                    if max_delay_hours < 1:
                        max_delay_hours = 1

                    comment_time = issue.created_at + timedelta(
                        hours=max_delay_hours,
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59),
                    )

                else:
                    # Later comments (follow-ups and updates)
                    content = random.choice(
                        comment_templates[12:] + follow_up_templates
                    )

                    # Later comments spread over days/weeks
                    comment_delay_days = random.choices(
                        [1, 2, 3, 5, 7, 10, 14, 21],
                        weights=[15, 15, 15, 15, 15, 10, 10, 5],
                    )[0]

                    # Make sure comment time doesn't exceed current time
                    max_delay_days = min(comment_delay_days, issue_age.days)
                    if max_delay_days < 1:
                        max_delay_days = 1

                    comment_time = issue.created_at + timedelta(
                        days=max_delay_days,
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                    )

                # Ensure comment time doesn't exceed current time
                if comment_time > now:
                    comment_time = now - timedelta(
                        hours=random.randint(1, 24), minutes=random.randint(0, 59)
                    )

                # Some variation in content based on user location
                if random.random() < 0.4 and author.location:
                    if author.location == issue.location:
                        content += f" I'm also in {author.location} and experiencing the same thing."
                    else:
                        content += f" Similar issue happening in {author.location} too."

                # Create the comment with custom timestamp
                comment = Comment.objects.create(
                    issue=issue, author=author, content=content, created_at=comment_time
                )
                comments.append(comment)

                # Create some replies to comments (with even later timestamps)
                if (
                    random.random() < 0.25 and i < num_comments - 1
                ):  # 25% chance of reply
                    reply_author = random.choice(users)

                    # Don't reply to your own comment
                    if reply_author == author:
                        reply_author = random.choice([u for u in users if u != author])

                    reply_templates = [
                        "I agree with your comment. We need to work together on this.",
                        "Thanks for sharing your experience. We're all affected.",
                        "Have you tried contacting the agency directly about this?",
                        "This is a community-wide problem that needs urgent attention.",
                        "Let me know if you find any temporary solutions.",
                        "We should document all these issues for follow-up.",
                        "Has the situation improved in your area since you posted this?",
                        "I've seen similar problems in neighboring communities too.",
                    ]

                    reply_content = random.choice(reply_templates)

                    # Replies come 1-48 hours after the original comment
                    reply_delay_hours = random.choices(
                        [1, 2, 4, 8, 12, 24, 48], weights=[20, 18, 15, 15, 12, 10, 10]
                    )[0]

                    reply_time = comment_time + timedelta(
                        hours=reply_delay_hours, minutes=random.randint(0, 59)
                    )

                    # Ensure reply time doesn't exceed current time
                    if reply_time > now:
                        reply_time = now - timedelta(minutes=random.randint(30, 180))

                    Comment.objects.create(
                        issue=issue,
                        author=reply_author,
                        content=reply_content,
                        parent_comment=comment,
                        created_at=reply_time,
                    )

        self.stdout.write(f"Created {len(comments)} comments with realistic timestamps")

    def create_engagement_data(self):
        """Create likes and reposts"""

        issues = list(Issue.objects.all())
        users = list(User.objects.all())

        # Create likes
        like_count = 0
        for issue in issues:
            # Random number of likes based on issue age and category
            max_likes = min(50, len(users) // 2)
            num_likes = random.randint(0, max_likes)

            likers = random.sample(users, min(num_likes, len(users)))
            for user in likers:
                Like.objects.get_or_create(user=user, issue=issue)
                like_count += 1

        # Create reposts
        repost_count = 0
        for issue in issues:
            # Fewer reposts than likes
            max_reposts = min(20, len(users) // 4)
            num_reposts = random.randint(0, max_reposts)

            reposters = random.sample(users, min(num_reposts, len(users)))
            for user in reposters:
                comment = random.choice(
                    [
                        "",
                        "This needs immediate attention!",
                        "Everyone should see this",
                        "Shared for visibility",
                    ]
                )
                Repost.objects.get_or_create(
                    user=user, issue=issue, defaults={"comment": comment}
                )
                repost_count += 1

        self.stdout.write(f"Created {like_count} likes and {repost_count} reposts")

    def create_trending_topics(self):
        """Create trending topics"""

        topics = [
            ("#WaterShortage", "Kubwa", 47),
            ("#KubwaRoad", "Kubwa", 32),
            ("#PowerOutage", "Gwarinpa", 28),
            ("#GwarinpaLight", "Gwarinpa", 23),
            ("#AbujaTraffic", "Airport Road", 19),
            ("#WasteManagement", "Garki", 15),
            ("#HealthcareServices", "Wuse", 12),
            ("#SecurityConcerns", "Nyanya", 18),
            ("#RoadMaintenance", "Maitama", 14),
            ("#EnvironmentProtection", "Asokoro", 11),
        ]

        for tag, location, count in topics:
            TrendingTopic.objects.get_or_create(
                tag=tag, location=location, defaults={"count": count}
            )

        self.stdout.write("Created trending topics")

    def create_notifications(self):
        """Create sample notifications"""

        users = list(User.objects.filter(user_type="citizen")[:20])
        issues = list(Issue.objects.all()[:50])

        notification_count = 0
        for user in users:
            # Create 3-8 notifications per user
            num_notifications = random.randint(3, 8)

            for _ in range(num_notifications):
                issue = random.choice(issues)
                notif_type = random.choice(
                    ["like", "comment", "agency_response", "status_update"]
                )

                titles_and_messages = {
                    "like": (
                        f"Your issue received a like",
                        f'Your issue "{issue.title[:50]}..." received a like',
                    ),
                    "comment": (
                        "New comment on your issue",
                        f'Someone commented on "{issue.title[:50]}..."',
                    ),
                    "agency_response": (
                        "Agency responded to your issue",
                        f'An agency responded to your issue "{issue.title[:50]}..."',
                    ),
                    "status_update": (
                        "Issue status updated",
                        f"Your issue status changed to {issue.get_status_display()}",
                    ),
                }

                title, message = titles_and_messages[notif_type]

                Notification.objects.create(
                    recipient=user,
                    notification_type=notif_type,
                    title=title,
                    message=message,
                    issue=issue,
                    is_read=random.choice([True, False]),
                )
                notification_count += 1

        self.stdout.write(f"Created {notification_count} notifications")
