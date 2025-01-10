"""
Test Recipe endpoints.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPE_LIST_URL = reverse('recipe:recipe-list')


def get_detail_url(recipe_id):
    """Create and return a Recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample Recipe"""
    defaults = {
        'title': 'Sample Recipe',
        'time_in_min': 5,
        'price': Decimal('5.21'),
        'description': 'This is a sample recipe',
        'link': 'http://example.com/sample-recipe.pdf'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests for Recipe."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Tests that authentication is required to list Recipies"""
        res = self.client.get(RECIPE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Tests authenticated API requests for Recipe."""

    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Tests successful retrieval for list of recipies of the user"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_LIST_URL)

        recipies = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieved_recipies_limited_to_user(self):
        """
        Tests that retrieved recipies are limited
        to authenticated User only
        """
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='somepassword123'
        )

        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_LIST_URL)

        recipies = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test to get the Recipe detail"""
        recipe = create_recipe(user=self.user)

        res = self.client.get(path=get_detail_url(recipe.id))

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Test Title',
            'time_in_min': 20,
            'price': Decimal('3.99')
        }
        res = self.client.post(RECIPE_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of Receipe."""
        org_link = "https://example.com/org-recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title='Test Recipe',
            link=org_link,
        )

        payload = {'title': 'New Title'}
        url = get_detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, org_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of Recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Test Recipe',
            description='This is a sample recipe',
            link='https://examle.com/recipe.pdf'
        )

        payload = {
            'title': 'New title Receipe',
            'description': 'New description of the recipe.',
            'time_in_min': 10,
            'price': Decimal('11.11'),
            'link': 'https://example.com/new-recipe.pdf'
        }

        res = self.client.put(get_detail_url(recipe.id), payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_user_update_is_not_allowed(self):
        """Test that user of a Receipe cannot be updated."""
        another_user = get_user_model().objects.create_user(
            email='another@example.com',
            password='somepassword123',
        )
        receipe = create_recipe(user=self.user)

        payload = {'user': another_user.id}

        self.client.patch(get_detail_url(receipe.id), payload)

        receipe.refresh_from_db()
        self.assertEqual(receipe.user, self.user)

    def test_delete_recipe(self):
        """Test deletion of Recipe"""
        recipe = create_recipe(user=self.user)
        res = self.client.delete(get_detail_url(recipe.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_other_user_recipe_deletion_not_allowed(self):
        """Test that Recipe of other users cannot be deleted"""
        new_user = get_user_model().objects.create_user(
            email='user2@example.com',
            password='test123'
        )
        recipe = create_recipe(user=new_user)

        res = self.client.delete(get_detail_url(recipe.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
