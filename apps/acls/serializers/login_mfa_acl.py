from django.utils.translation import gettext_lazy as _

from common.serializers import CommonBulkModelSerializer
from common.serializers import MethodSerializer
from common.serializers.fields import LabeledChoiceField
from .base import BaseUserACLSerializer
from .rules import RuleSerializer
from ..const import ActionChoices
from ..models import LoginMFAACL
from authentication.const import MFAType


__all__ = ["LoginMFAACLSerializer"]

common_help_text = _("With * indicating a match all. ")


class LoginMFAACLSerializer(BaseUserACLSerializer, CommonBulkModelSerializer):
    rules = MethodSerializer(label=_('Rule'))
    mfa_type = LabeledChoiceField(
        choices=MFAType.choices,
        default=MFAType.OTP,
        label=_('MFA type')
    )

    class Meta(BaseUserACLSerializer.Meta):
        model = LoginMFAACL
        fields = list((set(BaseUserACLSerializer.Meta.fields) | {'rules', 'mfa_type'}))
        action_choices_exclude = [
            ActionChoices.review,
            ActionChoices.warning,
            ActionChoices.notice,
            ActionChoices.notify_and_warn,
            ActionChoices.face_verify,
            ActionChoices.face_online,
            ActionChoices.change_secret
        ]

    def get_rules_serializer(self):
        return RuleSerializer()