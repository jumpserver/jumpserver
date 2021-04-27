from rest_framework.mixins import ListModelMixin

from common.drf.api import JMSBulkModelViewSet, JmsGenericViewSet, JMSBulkRelationModelViewSet
from .models import Subscription, Backend, Message
from .serializers import (
    SubscriptionSerializer, BackendSerializer, MessageSerializer,
    SubscriptionUserRelationSerializer, SubscriptionGroupRelationSerializer,
    SubscriptionBackendRelationSerializer, SubscriptionMessageRelationSerializer,
    SubscriptionListSerializer,
)


class SubscriptionViewSet(JMSBulkModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    serializer_classes = {
        'default': SubscriptionSerializer,
        'list': SubscriptionListSerializer
    }


class SubscriptionUserRelationViewSet(JMSBulkRelationModelViewSet):
    serializer_class = SubscriptionUserRelationSerializer
    m2m_field = Subscription.users.field


class SubscriptionGroupRelationViewSet(JMSBulkRelationModelViewSet):
    serializer_class = SubscriptionGroupRelationSerializer
    m2m_field = Subscription.groups.field


class SubscriptionBackendRelationViewSet(JMSBulkRelationModelViewSet):
    serializer_class = SubscriptionBackendRelationSerializer
    m2m_field = Subscription.receive_backends.field


class SubscriptionMessageRelationViewSet(JMSBulkRelationModelViewSet):
    serializer_class = SubscriptionMessageRelationSerializer
    m2m_field = Subscription.messages.field


class BackendViewSet(ListModelMixin, JmsGenericViewSet):
    queryset = Backend.objects.all()
    serializer_class = BackendSerializer


class MessageViewSet(ListModelMixin, JmsGenericViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
