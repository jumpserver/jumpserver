from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from ..models import ConnectMethodACL

__all__ = ["ConnectMethodACLSerializer"]


class ConnectMethodACLSerializer(BaseSerializer, BulkOrgResourceModelSerializer):
    class Meta(BaseSerializer.Meta):
        model = ConnectMethodACL
        fields = [
            i for i in BaseSerializer.Meta.fields + ['connect_methods']
            if i not in ['assets', 'accounts']
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_action = self.fields.get('action')
        if not field_action:
            return
        # 仅支持拒绝
        for k in ['review', 'accept']:
            field_action._choices.pop(k, None)
