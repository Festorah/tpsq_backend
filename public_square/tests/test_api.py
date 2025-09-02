import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class APITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_issue_list_api(self):
        response = self.client.get("/api/issues/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

    def test_issue_creation_api(self):
        csrf_response = self.client.get("/api/csrf/")
        csrf_token = csrf_response.json()["csrfToken"]

        data = {
            "title": "Test Issue",
            "content": "Test content",
            "category": "water",
            "location": "Test Location",
        }

        response = self.client.post(
            "/api/issues/",
            data=json.dumps(data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
