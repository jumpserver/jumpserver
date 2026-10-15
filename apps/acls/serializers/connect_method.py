from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import JSONManyToManyField
from common.serializers.mixin import CommonBulkModelSerializer
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from ..const import ActionChoices
from ..models import ConnectMethodACL

__all__ = ["ConnectMethodACLSerializer"]


class ConnectMethodACLSerializer(BaseSerializer, CommonBulkModelSerializer):
    assets = JSONManyToManyField(label=_('Asset'), required=False)
    connect_methods = serializers.ListField(
        child=serializers.CharField(), required=True, allow_empty=False,
        label=_('Connect methods'),
        error_messages={
            'required': _('Select at least one connection method'),
            'empty': _('Select at least one connection method'),
        },
    )

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
