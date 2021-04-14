from orgs.mixins.api import OrgGenericViewSet, OrgBulkModelViewSet, OrgRelationMixin
from .models import Subscription
from .serializers import SubscriptionSerializer


class SubscriptionViewSet(OrgBulkModelViewSet):
    model = Subscription
    serializer_class = SubscriptionSerializer
