from django.utils.translation import gettext_lazy as _

from common.serializers import MethodSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from .rules import RuleSerializer
from ..models import LoginAssetACL

__all__ = ["LoginAssetACLSerializer"]


class LoginAssetACLSerializer(BaseSerializer, BulkOrgResourceModelSerializer):
    rules = MethodSerializer(label=_('Rule'))

    class Meta(BaseSerializer.Meta):
        model = LoginAssetACL
        fields = BaseSerializer.Meta.fields + ['rules']

    def get_rules_serializer(self):
        return RuleSerializer()
