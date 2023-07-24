from django.utils.translation import gettext as _

from common.serializers import MethodSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserACLSerializer
from .rules import RuleSerializer
from ..models import LoginACL

__all__ = ["LoginACLSerializer"]

common_help_text = _("With * indicating a match all. ")


class LoginACLSerializer(BaseUserACLSerializer, BulkOrgResourceModelSerializer):
    rules = MethodSerializer(label=_('Rule'))

    class Meta(BaseUserACLSerializer.Meta):
        model = LoginACL
        fields = BaseUserACLSerializer.Meta.fields + ['rules', ]

    def get_rules_serializer(self):
        return RuleSerializer()
