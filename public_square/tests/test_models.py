import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from public_square.models import Category, Comment, Issue
from public_square.services import IssueService

User = get_user_model()


class IssueModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.category = Category.objects.create(
            name="Water", slug="water", description="Water related issues"
        )

    def test_issue_creation(self):
        issue = Issue.objects.create(
            title="Water shortage",
            content="No water for 3 days",
            author=self.user,
            category=self.category,
            location="Kubwa",
        )
        self.assertEqual(issue.status, "pending")
        self.assertTrue(issue.is_active)

    def test_issue_service(self):
        issue = IssueService.create_issue(
            author=self.user,
            title="Test Issue",
            content="Test content for issue",
            category_slug="water",
            location="Test Location",
        )
        self.assertEqual(issue.category, self.category)
        self.assertEqual(issue.location, "Test Location")
