from django.db.models import TextChoices
from rest_framework import serializers


class FieldDefinitionTypeChoices(TextChoices):
    char = 'char', 'CharField'
    integer = 'integer', 'IntegerField'
    boolean = 'boolean', 'BooleanField'
    datetime = 'datetime', 'DateTimeField'
    ip_address = 'ip_address', 'IPAddressField'
    array = 'array', 'ListField'

    @classmethod
    def get_serializer_field_class(cls, tp):
        assert tp in cls.names, 'Invalid type: {}'.format(tp)
        label = getattr(getattr(cls, tp), 'label')
        serializer_class = getattr(serializers, label)
        return serializer_class
