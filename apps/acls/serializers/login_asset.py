
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import models


__all__ = ['LoginAssetACLSerializer']


class LoginAssetACLUsersSerializer(serializers.Serializer):
    username = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Username'),
        help_text=_('')
    )


class LoginAssetACLSystemUsersSerializer(serializers.Serializer):
    name = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Name')
    )
    username = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Username')
    )
    protocol = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=16), label=_('Protocol')
    )


class LoginAssetACLAssestsSerializer(serializers.Serializer):
    ip = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=1024), label=_('IP')
    )
    hostname = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Hostname')
    )


class LoginAssetACLSerializer(BulkOrgResourceModelSerializer):
    users = LoginAssetACLUsersSerializer()
    system_users = LoginAssetACLSystemUsersSerializer()
    assets = LoginAssetACLAssestsSerializer()

    class Meta:
        model = models.LoginAssetACL
        fields = [
            'id', 'name', 'priority', 'users', 'system_users', 'assets', 'action', 'comment',
            'reviewers', 'created_by', 'date_created', 'date_updated', 'org_id',
        ]
