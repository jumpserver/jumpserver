from uuid import UUID

from django.utils.translation import gettext as _
from rest_framework import serializers


__all__ = ['UserGroupTreeQuerySerializer']


class UserGroupTreeQuerySerializer(serializers.Serializer):
    parent_type = serializers.ChoiceField(
        choices=('organization', 'user_group'),
        required=False,
    )
    parent_id = serializers.CharField(
        max_length=128, required=False, allow_blank=False,
    )
    search = serializers.CharField(
        max_length=256, required=False, allow_blank=False,
        trim_whitespace=True,
    )
    order = serializers.ChoiceField(
        choices=('name', 'username'), default='name', required=False,
    )
    limit = serializers.IntegerField(
        min_value=1, max_value=1000, default=1000, required=False,
    )
    offset = serializers.IntegerField(
        min_value=0, max_value=1000000, default=0, required=False,
    )

    def validate(self, attrs):
        parent_type = attrs.get('parent_type')
        parent_id = attrs.get('parent_id')
        if bool(parent_type) != bool(parent_id):
            raise serializers.ValidationError(
                _('parent_type and parent_id must be provided together.')
            )
        if attrs.get('search') and parent_type:
            raise serializers.ValidationError(
                _('Search and parent parameters cannot be used together.')
            )
        if attrs['offset'] and not parent_type:
            raise serializers.ValidationError({
                'offset': _('Offset is only supported when loading children.'),
            })
        if parent_type in ('organization', 'user_group'):
            try:
                UUID(parent_id)
            except (TypeError, ValueError):
                raise serializers.ValidationError({
                    'parent_id': _('Enter a valid UUID.'),
                })
        return attrs
