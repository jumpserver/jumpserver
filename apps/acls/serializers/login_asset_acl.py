
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from acls import models


__all__ = ['LoginAssetACLSerializer']


class LoginAssetACLUsersSerializer(serializers.Serializer):
    username_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Username'),
        help_text=_('')
    )


class LoginAssetACLAssestsSerializer(serializers.Serializer):
    ip_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=1024), label=_('IP')
    )
    hostname_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Hostname')
    )


class LoginAssetACLSystemUsersSerializer(serializers.Serializer):
    name_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Name')
    )
    username_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Username')
    )
    protocol_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=16), label=_('Protocol')
    )


class LoginAssetACLSerializer(BulkOrgResourceModelSerializer):
    users = LoginAssetACLUsersSerializer()
    assets = LoginAssetACLAssestsSerializer()
    system_users = LoginAssetACLSystemUsersSerializer()

    class Meta:
        model = models.LoginAssetACL
        fields = [
            'id', 'name', 'priority', 'users', 'system_users', 'assets', 'action', 'comment',
            'reviewers', 'created_by', 'date_created', 'date_updated', 'org_id',
        ]
