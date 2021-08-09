from rest_framework.mixins import ListModelMixin, UpdateModelMixin

from common.drf.api import JmsGenericViewSet
from .models import Backend, Message
from .serializers import (
    BackendSerializer, MessageSerializer,
)


class BackendViewSet(ListModelMixin, JmsGenericViewSet):
    queryset = Backend.objects.all()
    serializer_class = BackendSerializer


class MessageViewSet(ListModelMixin, UpdateModelMixin, JmsGenericViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
