from django.utils.translation import ugettext_lazy as _

from acls.models import CommandGroup, CommandFilterACL
from common.drf.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserAssetAccountACLSerializerMixin as BaseSerializer

__all__ = ["CommandFilterACLSerializer", "CommandGroupSerializer"]


class CommandGroupSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = CommandGroup
        fields = ['id', 'name', 'type', 'content', 'comment']


class CommandFilterACLSerializer(BaseSerializer, BulkOrgResourceModelSerializer):
    commands = ObjectRelatedField(queryset=CommandGroup.objects, many=True, required=False, label=_('Commands'))

    class Meta(BaseSerializer.Meta):
        model = CommandFilterACL
        fields = BaseSerializer.Meta.fields + ['commands']
