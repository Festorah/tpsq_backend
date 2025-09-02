import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Category, Comment, Issue, User


class IssueCreateForm(forms.ModelForm):
    """Form for creating issues"""

    class Meta:
        model = Issue
        fields = ["title", "content", "category", "location", "latitude", "longitude"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Brief title for your issue",
                    "maxlength": 200,
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Describe the issue in detail. Include location, when it started, and how it affects you or your community.",
                    "required": True,
                }
            ),
            "category": forms.Select(attrs={"class": "form-select", "required": True}),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Kubwa Phase 2, Gwarinpa Estate, Airport Road",
                    "required": True,
                }
            ),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["category"].empty_label = "Select a category"

    def clean_content(self):
        content = self.cleaned_data.get("content")
        if len(content) < 10:
            raise ValidationError(
                "Issue description must be at least 10 characters long."
            )
        return content

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if not title:
            # Auto-generate title from content if not provided
            content = self.cleaned_data.get("content", "")
            if content:
                title = content.split(".")[0][:100]
                if not title.endswith("."):
                    title += "..."
        return title


class CommentForm(forms.ModelForm):
    """Form for creating comments"""

    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Add a comment...",
                    "required": True,
                }
            )
        }

    def clean_content(self):
        content = self.cleaned_data.get("content")
        if len(content) < 3:
            raise ValidationError("Comment must be at least 3 characters long.")
        return content


class UserRegistrationForm(UserCreationForm):
    """User registration form"""

    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First Name",
                "required": True,
            }
        ),
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Last Name",
                "required": True,
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email Address",
                "required": True,
            }
        )
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+234XXXXXXXXXX",
                "required": True,
            }
        ),
    )
    location = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Your location in FCT (e.g., Kubwa, Gwarinpa)",
                "required": True,
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "location",
            "password1",
            "password2",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Choose a username"}
            )
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        if phone:
            # Remove spaces and format
            phone = re.sub(r"\s+", "", phone)
            if not phone.startswith("+234") and phone.startswith("0"):
                phone = "+234" + phone[1:]
            elif not phone.startswith("+234") and not phone.startswith("234"):
                phone = "+234" + phone

            # Validate format
            if not re.match(r"^\+?234\d{10}$", phone):
                raise ValidationError("Enter a valid Nigerian phone number")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email


class UserProfileForm(forms.ModelForm):
    """User profile edit form"""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "location",
            "bio",
            "avatar",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Tell us about yourself...",
                }
            ),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
        }


class SearchForm(forms.Form):
    """Search form"""

    q = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search issues...",
                "required": False,
            }
        ),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        empty_label="All Categories",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Location"}
        ),
    )
    status = forms.ChoiceField(
        choices=[("", "All Statuses")] + Issue.Status.choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
