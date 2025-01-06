"""
Serializer for Receipe APIs.
"""

from rest_framework.serializers import ModelSerializer

from core.models import Recipe


class RecipeSerializer(ModelSerializer):
    """Serializers for Recipe."""

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_in_min', 'price', 'description', 'link']
        read_only_fields = ['id']
