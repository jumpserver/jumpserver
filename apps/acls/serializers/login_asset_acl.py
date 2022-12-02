from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import BaseUserAssetAccountACLSerializerMixin as BaseSerializer
from ..models import LoginAssetACL

__all__ = ["LoginAssetACLSerializer"]


class LoginAssetACLSerializer(BaseSerializer, BulkOrgResourceModelSerializer):
    class Meta(BaseSerializer.Meta):
        model = LoginAssetACL
