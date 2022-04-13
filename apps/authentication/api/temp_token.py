from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import action

from common.drf.api import JMSModelViewSet
from common.permissions import IsValidUser
from ..models import TempToken
from ..serializers import TempTokenSerializer


class TempTokenViewSet(JMSModelViewSet):
    serializer_class = TempTokenSerializer
    permission_classes = [IsValidUser]
    http_method_names = ['post', 'get', 'options', 'patch']

    def get_queryset(self):
        username = self.request.user.username
        return TempToken.objects.filter(username=username)

    @action(methods=['PATCH'], detail=True, url_path='expire')
    def expire(self, *args, **kwargs):
        instance = self.get_object()
        instance.date_expired = timezone.now()
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

