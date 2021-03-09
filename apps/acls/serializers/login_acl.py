from common.mixins.serializers import BulkSerializerMixin
from rest_framework import serializers
from ..models import LoginACL


__all__ = ['LoginACLSerializer']


class LoginACLSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = LoginACL
        fields = [
            'id', 'name', 'priority', 'ip_group', 'users', 'action', 'comment', 'created_by',
            'date_created', 'date_updated'
        ]
