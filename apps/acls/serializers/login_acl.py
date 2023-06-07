from django.utils.translation import ugettext as _

from common.serializers import MethodSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaserUserACLSerializer
from .rules import RuleSerializer
from ..models import LoginACL

__all__ = ["LoginACLSerializer"]

common_help_text = _("With * indicating a match all. ")


class LoginACLSerializer(BaserUserACLSerializer, BulkOrgResourceModelSerializer):
    rules = MethodSerializer(label=_('Rule'))

    class Meta(BaserUserACLSerializer.Meta):
        model = LoginACL
        fields = BaserUserACLSerializer.Meta.fields + ['rules', ]

    def get_rules_serializer(self):
        return RuleSerializer()
