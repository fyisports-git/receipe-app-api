"""
Serializer for Receipe APIs.
"""

from rest_framework.serializers import ModelSerializer

from core.models import Recipe


class RecipeSerializer(ModelSerializer):
    """Serializers for Recipe."""

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_in_min', 'price', 'link']
        read_only_fields = ['id']


class RecipeDetailSerializer(RecipeSerializer):
    """Serialier for Recipe details"""

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']
