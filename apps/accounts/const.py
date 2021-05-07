from django.db.models import TextChoices
from rest_framework import serializers

from rest_framework import serializers


class PropertyTypeChoices(TextChoices):
    str = 'str', 'CharField'
    int = 'int', 'IntegerField'
    bool = 'bool', 'BooleanField'
    list = 'list', 'ListField'
    ip = 'ip', 'IPAddressField'
    datetime = 'datetime', 'DateTimeField'

    @classmethod
    def get_serializer_field_class(cls, tp):
        assert tp in cls.names, 'Invalid type: {}'.format(tp)
        label = getattr(getattr(cls, tp), 'label')
        serializer_class = getattr(serializers, label)
        return serializer_class
