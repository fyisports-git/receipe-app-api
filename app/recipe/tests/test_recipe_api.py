"""
Test Recipe endpoints.
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPE_LIST_URL = reverse('recipe:recipe-list')


def get_detail_url(recipe_id):
    """Create and return a Recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return an image upload URL"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


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

    def test_create_recipe_with_new_tags(self):
        """Test create a recipe with new tags"""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_in_min': 30,
            'price': Decimal('22.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPE_LIST_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        """Test creating a recipe with an existing tag"""
        tag_indian = Tag.objects.create(user=self.user, name="indian")
        payload = {
            'title': 'Pongal',
            'time_in_min': 60,
            'price': Decimal('12.50'),
            'tags': [{'name': 'indian'}, {'name': 'breakfast'}]
        }

        res = self.client.post(RECIPE_LIST_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

        tags = Tag.objects.filter(user=self.user)
        self.assertEqual(tags.count(), 2)
        for tag in payload['tags']:
            exists = Tag.objects.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a new tag while updating a recipe"""
        recipe = create_recipe(user=self.user)

        payload = {
            'tags': [{'name': 'lunch'}]
        }
        url = get_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an exsiting tag when updating a recipe"""
        tag_breakfast = Tag.objects.create(user=self.user, name='breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='lunch')
        payload = {
            'tags': [{'name': 'lunch'}]
        }
        url = get_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Test clearing recipe tags"""
        tag = Tag.objects.create(user=self.user, name='dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}

        url = get_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test create a recipe with new ingredients"""
        payload = {
            'title': 'Cauliflower Tacos',
            'time_in_min': 30,
            'price': Decimal('22.50'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}]
        }
        res = self.client.post(RECIPE_LIST_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a recipe with an existing ingredient"""
        ingredient_lemon = Ingredient.objects.create(
            user=self.user,
            name="Lemon")
        payload = {
            'title': 'Vietnamese Soup',
            'time_in_min': 25,
            'price': Decimal('2.50'),
            'ingredients': [{'name': 'Lemon'}, {'name': 'Fish Sauce'}]
        }

        res = self.client.post(RECIPE_LIST_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_lemon, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating a new ingredient while updating a recipe"""
        recipe = create_recipe(user=self.user)

        payload = {
            'ingredients': [{'name': 'tomato'}]
        }
        url = get_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='tomato')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an exsiting ingredient when updating a recipe"""
        ingredient_new = Ingredient.objects.create(
            user=self.user,
            name='paneer')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_new)

        ingredient_another = Ingredient.objects.create(
            user=self.user,
            name='chilli')
        payload = {
            'ingredients': [{'name': 'chilli'}]
        }
        url = get_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_another, recipe.ingredients.all())
        self.assertNotIn(ingredient_new, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing recipe ingredients"""
        ingredient = Ingredient.objects.create(user=self.user, name='garlic')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}

        url = get_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)


class ImageUploadTests(TestCase):
    """Tests for image upload api"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image"""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'not an image'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
