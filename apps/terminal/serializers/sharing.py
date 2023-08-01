from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from common.utils.common import pretty_string
from common.utils.random import random_string
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from ..const import ActionPermission
from ..models import SessionSharing, SessionJoinRecord

__all__ = ['SessionSharingSerializer', 'SessionJoinRecordSerializer']


class SessionSharingSerializer(OrgResourceModelSerializerMixin):
    users = serializers.ListSerializer(
        child=serializers.CharField(max_length=36), allow_null=True, write_only=True
    )
    action_permission = LabeledChoiceField(
        default=ActionPermission.writable, choices=ActionPermission.choices,
        write_only=True, label=_('Action permission')
    )

    class Meta:
        model = SessionSharing
        fields_mini = ['id']
        fields_small = fields_mini + [
            'verify_code', 'is_active', 'expired_time', 'created_by',
            'date_created', 'date_updated', 'users', 'users_display',
            'action_permission', 'origin', 'url',
        ]
        fields_fk = ['session', 'creator']
        fields = fields_small + fields_fk
        read_only_fields = ['verify_code']

    def save(self, **kwargs):
        users = self.validated_data.get('users', [])
        self.validated_data['users'] = ','.join(users)
        return super().save(**kwargs)

    def create(self, validated_data):
        validated_data['verify_code'] = random_string(4)
        session = validated_data.get('session')
        if session:
            validated_data['creator_id'] = session.user_id
            validated_data['created_by'] = pretty_string(str(session.user), max_length=32)
            validated_data['org_id'] = session.org_id
        return super().create(validated_data)


class SessionJoinRecordSerializer(OrgResourceModelSerializerMixin):
    action_permission = LabeledChoiceField(
        choices=ActionPermission.choices, read_only=True, label=_('Action permission')
    )

    class Meta:
        model = SessionJoinRecord
        fields_mini = ['id']
        fields_small = fields_mini + [
            'joiner_display', 'verify_code', 'date_joined', 'date_left',
            'remote_addr', 'login_from', 'is_success', 'reason', 'is_finished',
            'created_by', 'date_created', 'date_updated', 'action_permission'
        ]
        fields_fk = ['session', 'sharing', 'joiner']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'session': {'required': False},
            'joiner': {'required': True},
            'sharing': {'required': True},
            'remote_addr': {'required': True},
            'verify_code': {'required': True},
            'joiner_display': {'label': _('Joiner')},
        }

    def create(self, validate_data):
        sharing = validate_data.get('sharing')
        if sharing:
            validate_data['session'] = sharing.session
            validate_data['org_id'] = sharing.org_id
        return super().create(validate_data)
