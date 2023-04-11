from rest_framework import serializers

from assets.models import Database, Web


class DatabaseSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = Database
        fields = ['db_name', 'use_ssl', 'allow_invalid_cert']


class WebSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = Web
        fields = [
            'autofill', 'username_selector', 'password_selector',
            'submit_selector', 'script'
        ]


category_spec_serializer_map = {
    'database': DatabaseSpecSerializer,
    'web': WebSpecSerializer,
}
