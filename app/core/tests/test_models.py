"""Tests for Models"""

from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def create_user(email="test@example.com", password="testpassword123"):
    """Create and return a test user with default values"""
    return get_user_model().objects.create_user(email, password)


class ModelsTests(TestCase):
    """Test Models"""

    def test_create_user_with_email_successful(self):
        """Test creating a user using email id is successful."""
        email = "test@example.com"
        password = "something"
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_email_normalisation(self):
        """Test that new email ids are getting normalized."""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com']
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(
                email=email,
                password='default123'
            )
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test that email address is a required field"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """Test creating a Super User."""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_recipe_creation_successful(self):
        """Test Recipe creation is successful"""
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpassword123',
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample recipe',
            time_in_min=5,
            price=Decimal('5.50'),
            description='This is a sample recipe.'
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test creating a tag is successful."""
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')

        self.assertEqual(str(tag), tag.name)
