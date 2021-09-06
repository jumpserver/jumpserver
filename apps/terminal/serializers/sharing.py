from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from common.utils.random import random_string
from ..models import SessionSharing

__all__ = ['SessionSharingSerializer']


class SessionSharingSerializer(OrgResourceModelSerializerMixin):

    class Meta:
        model = SessionSharing
        fields_mini = ['id']
        fields_small = fields_mini + [
            'verify_code', 'is_active', 'expired_time', 'created_by',
            'date_created', 'date_updated'
        ]
        fields_fk = ['session', 'creator']
        fields = fields_small + fields_fk

        extra_kwargs = {
            'verify_code': {'write_only': True, 'required': False}
        }

    def create(self, validated_data):
        validated_data['verify_code'] = random_string(4)
        session = validated_data.get('session')
        if session:
            validated_data['org_id'] = session.org_id
            validated_data['creator_id'] = session.user_id
        return super().create(validated_data)
