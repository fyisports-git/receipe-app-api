"""
Tests for User API
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
CREATE_TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    """Create and return a new User"""
    return get_user_model().objects.create_user(**params)


class PublicUserAPITests(TestCase):
    """Test cases for the public APIs of Users"""

    def setUp(self):
        self.client = APIClient()

    def test_user_create_success(self):
        """Test creating a User is successful"""
        payload = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'name': 'Test User',
        }
        res = self.client.post(path=CREATE_USER_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_email_already_exist_error(self):
        """Test that User cannot be created with existing email id"""
        payload = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'name': 'Test User',
        }

        create_user(**payload)
        res = self.client.post(path=CREATE_USER_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test that too short password is not allowed"""
        payload = {
            'email': 'test@example.com',
            'password': 'pw',
            'name': 'Test User',
        }

        res = self.client.post(path=CREATE_USER_URL, data=payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email'],
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token(self):
        """Tests create token API"""
        user_details = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'name': 'Test User'
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }
        res = self.client.post(path=CREATE_TOKEN_URL, data=payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_with_wrong_password(self):
        """Test tokens won't get created if password is wrong"""
        user_details = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'name': 'Test User'
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': 'wrongpassword'
        }
        res = self.client.post(path=CREATE_TOKEN_URL, data=payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_with_blank_password(self):
        """Test tokens won't get created if password is blank"""
        user_details = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'name': 'Test User'
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': ''
        }
        res = self.client.post(path=CREATE_TOKEN_URL, data=payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_auth_required_to_retrieve(self):
        """Test authentication is required to retrieve User."""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserAPITests(TestCase):
    """Test APIs that require user authentication"""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='testpassword123',
            name='Test User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_user_retrieval_success(self):
        """Test successful retrieval of User"""
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email,
        })

    def test_post_method_not_allowed_for_me(self):
        res = self.client.post(path=ME_URL, data={})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test successful update of user profile post authentication"""
        payload = {
            'name': 'Updated Name',
            'password': 'newpassword123'
        }
        res = self.client.patch(path=ME_URL, data=payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload.get('name'))
        self.assertTrue(self.user.check_password(payload.get('password')))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
