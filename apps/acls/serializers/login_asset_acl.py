from rest_framework import serializers
from django.utils.translation import ugettext as _
from common.drf.fields import ReadableHiddenField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.models import SystemUser
from acls import models
from orgs.models import Organization
from .. import const


__all__ = ['LoginAssetACLSerializer']


class LoginAssetACLUsersSerializer(serializers.Serializer):
    username_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Username'),
        help_text=const.common_help_text
    )


class LoginAssetACLAssestsSerializer(serializers.Serializer):
    ip_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=1024), label=_('IP'),
        help_text=const.ip_group_help_text + _('Domain name support.')
    )
    hostname_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Hostname'),
        help_text=const.common_help_text
    )


class LoginAssetACLSystemUsersSerializer(serializers.Serializer):
    name_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Name'),
        help_text=const.common_help_text
    )
    username_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=128), label=_('Username'),
        help_text=const.common_help_text
    )
    protocol_group = serializers.ListField(
        default=['*'], child=serializers.CharField(max_length=16), label=_('Protocol'),
        help_text=const.common_help_text + _('Protocol options: {}').format(
            ', '.join(SystemUser.ASSET_CATEGORY_PROTOCOLS)
        )
    )

    @staticmethod
    def validate_protocol_group(protocol_group):
        unsupported_protocols = set(protocol_group) - set(SystemUser.ASSET_CATEGORY_PROTOCOLS + ['*'])
        if unsupported_protocols:
            raise serializers.ValidationError(_(f'Unsupported protocols: {unsupported_protocols}'))
        return protocol_group


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

    def validate_reviewers(self, reviewers):
        org_id = self.fields['org_id'].default()
        org = Organization.get_instance(org_id)
        if not org:
            error = _('The current organization `{}` is None'.format(org_id))
            raise serializers.ValidationError(error)
        users = org.get_members()
        valid_reviewers = list(set(reviewers) & set(users))
        if not valid_reviewers:
            error = _('None of the reviewers belong to Organization `{}`'.format(org.name))
            raise serializers.ValidationError(error)
        return valid_reviewers
