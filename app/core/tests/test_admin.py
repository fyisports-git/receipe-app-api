"""
Test for Django Admin modifications
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse


class AdminSiteTests(TestCase):
    """Tests for Django Admin modifications"""

    def setUp(self):
        """Create User and Client."""
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email='test-admin@example.com',
            password='testpassword123',
        )
        self.client.force_login(user=self.admin_user)
        self.user = get_user_model().objects.create_user(
            email='test-user@example.com',
            password='testpassword123',
            name='Test User'
        )

    def test_user_list(self):
        """Tests that users are listed."""
        url = reverse('admin:core_user_changelist')
        res = self.client.get(path=url)

        self.assertContains(res, self.user.name)
        self.assertContains(res, self.user.email)

    def test_user_edit_page(self):
        """Tests the User edit page"""
        url = reverse('admin:core_user_change', args=[self.user.id])
        res = self.client.get(path=url)

        self.assertEqual(res.status_code, 200)

    def test_user_add_page(self):
        """Tests User add page"""
        url = reverse('admin:core_user_add')
        res = self.client.get(path=url)

        self.assertEqual(res.status_code, 200)
