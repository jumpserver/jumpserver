from orgs.mixins.api import OrgBulkModelViewSet
from assets.models import AccountTemplate
from assets import serializers


class AccountTemplateViewSet(OrgBulkModelViewSet):
    model = AccountTemplate
    filterset_fields = ("username", 'name')
    search_fields = ('username', 'name')
    serializer_classes = {
        'default': serializers.AccountTemplateSerializer
    }
