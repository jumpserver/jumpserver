from django.utils.translation import ugettext_lazy as _

from acls.models import CommandGroup, CommandFilterACL
from common.drf.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserAssetAccountACLSerializerMixin

__all__ = ["CommandFilterACLSerializer"]


class CommandFilterACLSerializer(BaseUserAssetAccountACLSerializerMixin, BulkOrgResourceModelSerializer):
    commands = ObjectRelatedField(queryset=CommandGroup.objects, many=True, required=False, label=_('Commands'))

    class Meta(BaseUserAssetAccountACLSerializerMixin.Meta):
        model = CommandFilterACL
        fields = BaseUserAssetAccountACLSerializerMixin.Meta.fields + ['commands']
