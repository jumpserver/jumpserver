from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import BitChoicesField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.const import ActionChoices as PermActionChoices
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from ..const import ActionChoices
from ..models import ClipboardACL

__all__ = ['ClipboardACLSerializer', 'ClipboardOperationsField']


class ClipboardOperationsField(BitChoicesField):
    valid_operations = PermActionChoices.clipboard()

    def __init__(self, **kwargs):
        super().__init__(choice_cls=PermActionChoices, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if value == 0:
            raise serializers.ValidationError(_('At least one clipboard operation is required'))
        if value & ~self.valid_operations:
            raise serializers.ValidationError(_('Only copy and paste operations are allowed'))
        return value

    def to_representation(self, value):
        return [
            {'value': c.name, 'label': c.label}
            for c in PermActionChoices
            if c.value & self.valid_operations and c.value & value == c.value
        ]


class ClipboardACLSerializer(BaseSerializer, BulkOrgResourceModelSerializer):
    operations = ClipboardOperationsField(required=False, label=_('Operations'))

    class Meta(BaseSerializer.Meta):
        model = ClipboardACL
        fields = BaseSerializer.Meta.fields + [
            'operations',
            'copy_text_limit', 'paste_text_limit',
            'download_file_size_limit', 'upload_file_size_limit',
        ]
        action_choices_exclude = [
            ActionChoices.review,
            ActionChoices.warning,
            ActionChoices.notice,
            ActionChoices.notify_and_warn,
            ActionChoices.face_verify,
            ActionChoices.face_online,
            ActionChoices.change_secret,
        ]
