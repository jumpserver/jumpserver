
from assets.models import Database
from assets.serializers import DatabaseSerializer
from .asset import AssetViewSet

__all__ = ['DatabaseViewSet']


class DatabaseViewSet(AssetViewSet):
    model = Database

    def get_queryset(self):
        queryset = super().get_queryset()
        print("Datbase is: ", queryset)
        return queryset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = DatabaseSerializer
        return serializer_classes
