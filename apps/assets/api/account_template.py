from orgs.mixins.api import OrgBulkModelViewSet
from ..models import AccountTemplate
from .. import serializers


class AccountTemplateViewSet(OrgBulkModelViewSet):
    model = AccountTemplate
    filterset_fields = ("username", 'name')
    search_fields = ('username', 'name')
    serializer_classes = {
        'default': serializers.AccountTemplateSerializer
    }
