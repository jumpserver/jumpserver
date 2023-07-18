from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from ..models import ConnectMethodACL
from ..const import ActionChoices

__all__ = ["ConnectMethodACLSerializer"]


class ConnectMethodACLSerializer(BaseSerializer, BulkOrgResourceModelSerializer):
    class Meta(BaseSerializer.Meta):
        model = ConnectMethodACL
        fields = [
            i for i in BaseSerializer.Meta.fields + ['connect_methods']
            if i not in ['assets', 'accounts']
        ]
        action_choices_exclude = BaseSerializer.Meta.action_choices_exclude + [
            ActionChoices.review, ActionChoices.accept
        ]
