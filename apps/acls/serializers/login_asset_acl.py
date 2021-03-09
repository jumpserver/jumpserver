
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from acls import models
from orgs.models import Organization
from users.models import User


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
        extra_kwargs = {
            "reviewers": {'allow_null': False, 'required': True}
        }

    @staticmethod
    def validate_org_id(org_id):
        org = Organization.get_instance(org_id)
        if not org:
            error = _('The organization `{}` does not exist'.format(org_id))
            raise serializers.ValidationError(error)
        return org_id

    def validate_reviewers(self, reviewers):
        org_id = self.initial_data.get('org_id')
        self.validate_org_id(org_id)
        org = Organization.get_instance(org_id)
        users = org.get_members()
        valid_reviewers = list(set(reviewers) & set(users))
        if not valid_reviewers:
            error = _('None of the reviewers belong to Organization `{}`'.format(org.name))
            raise serializers.ValidationError(error)
        return valid_reviewers
