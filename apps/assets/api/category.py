from rest_framework.generics import ListAPIView

from assets.serializers import CategorySerializer, TypeSerializer
from assets.const import AllTypes

__all__ = ['CategoryListApi', 'TypeListApi']


class CategoryListApi(ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = ()

    def get_queryset(self):
        return AllTypes.categories()


class TypeListApi(ListAPIView):
    serializer_class = TypeSerializer
    permission_classes = ()

    def get_queryset(self):
        return AllTypes.types()
