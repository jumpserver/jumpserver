from rest_framework.viewsets import ModelViewSet

from common.permissions import IsValidUser
from ..models import TempToken
from ..serializers import TempTokenSerializer


class TempTokenViewSet(ModelViewSet):
    model = TempToken
    serializer_class = TempTokenSerializer
    permission_classes = [IsValidUser]
    http_method_names = ['post', 'option']
