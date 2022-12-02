from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .base import BaseUserAssetAccountACLSerializerMixin
from ..models import LoginAssetACL

__all__ = ["LoginAssetACLSerializer"]


class LoginAssetACLSerializer(BaseUserAssetAccountACLSerializerMixin, BulkOrgResourceModelSerializer):
    class Meta(BaseUserAssetAccountACLSerializerMixin.Meta):
        model = LoginAssetACL
