from rest_framework import serializers
from common.mixins.serializers import BulkSerializerMixin
from common.drf.serializers import AdaptedBulkListSerializer
from ..models import LoginACL


__all__ = ['LoginACLSerializer', 'LoginACLUserRelationSerializer']


class LoginACLSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = LoginACL
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'priority', 'ip_group', 'users', 'action', 'comment', 'created_by',
            'date_created', 'date_updated'
        ]


class LoginACLUserRelationSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    loginacl_display = serializers.ReadOnlyField(source='loginacl.name')
    user_display = serializers.ReadOnlyField()

    class Meta:
        model = LoginACL.users.through
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'loginacl', 'user', 'loginacl_display', 'user_display'
        ]


