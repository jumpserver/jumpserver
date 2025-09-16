from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response

from assets.const import AllTypes
from assets.serializers import CategorySerializer, TypeSerializer
from common.api import JMSGenericViewSet
from common.permissions import IsValidUser

__all__ = ['CategoryViewSet']


class CategoryViewSet(ListModelMixin, JMSGenericViewSet):
    serializer_classes = {
        'default': CategorySerializer,
        'types': TypeSerializer,
    }
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        return AllTypes.categories()

    @action(methods=['get'], detail=False)
    def types(self, request, *args, **kwargs):
        queryset = AllTypes.types()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def constraints(self, request, *args, **kwargs):
        category = request.query_params.get('category')
        tp = request.query_params.get('type')
        constraints = AllTypes.get_constraints(category, tp)
        return Response(constraints)
