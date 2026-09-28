from django.utils.translation import gettext_lazy as _

from common.serializers.fields import JSONManyToManyField
from common.serializers.mixin import CommonBulkModelSerializer
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from ..const import ActionChoices
from ..models import ConnectMethodACL

__all__ = ["ConnectMethodACLSerializer"]


class ConnectMethodACLSerializer(BaseSerializer, CommonBulkModelSerializer):
    assets = JSONManyToManyField(label=_('Asset'), required=False)

    class Meta(BaseSerializer.Meta):
        model = ConnectMethodACL
        fields = [
            i for i in BaseSerializer.Meta.fields + ['connect_methods']
            if i not in ['accounts', 'org_id']
        ]
        action_choices_exclude = BaseSerializer.Meta.action_choices_exclude + [
            ActionChoices.review,
            ActionChoices.notice,
            ActionChoices.face_verify,
            ActionChoices.face_online,
            ActionChoices.change_secret
        ]
