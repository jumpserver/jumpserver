from django.utils.translation import gettext as _

from common.serializers import CommonBulkModelSerializer
from common.serializers import MethodSerializer
from .base import BaseUserACLSerializer
from .rules import RuleSerializer
from ..const import ActionChoices
from ..models import LoginACL

__all__ = ["LoginACLSerializer"]

common_help_text = _("With * indicating a match all. ")


class LoginACLSerializer(BaseUserACLSerializer, CommonBulkModelSerializer):
    rules = MethodSerializer(label=_('Rule'))

    class Meta(BaseUserACLSerializer.Meta):
        model = LoginACL
        fields = list((set(BaseUserACLSerializer.Meta.fields) | {'rules'}) - {'org_id'})
        action_choices_exclude = [
            ActionChoices.warning,
            ActionChoices.notify_and_warn,
            ActionChoices.face_online,
            ActionChoices.face_verify,
            ActionChoices.change_secret
        ]

    def get_rules_serializer(self):
        return RuleSerializer()
