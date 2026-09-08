from uuid import UUID

from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response

from assets.models import Asset, FavoriteAsset, FavoriteFolder
from assets.serializers import FavoriteAssetSerializer
from common.utils.http import is_true
from perms import serializers
from perms.utils import (
    FAVORITE_ROOT_ID,
    get_user_asset_tree_metrics,
)
from ..mixin import SelfOrPKUserMixin


__all__ = ['UserFavoriteTreeApi', 'UserAssetTreeMetricsApi']


def _folder_key(folder_id):
    return f'favorite-folder:{folder_id}'


class UserFavoriteTreeApi(SelfOrPKUserMixin, ListAPIView):
    """Return a user's favorite folders and their directly contained assets."""

    @staticmethod
    def _folder_node(folder):
        parent_key = (
            _folder_key(folder.parent_id)
            if folder.parent_id else FAVORITE_ROOT_ID
        )
        return {
            'id': _folder_key(folder.id),
            'name': folder.name,
            'title': folder.name,
            'pId': parent_key,
            'open': False,
            'isParent': True,
            'hasChildren': True,
            'meta': {
                'type': 'node',
                'data': {
                    'id': str(folder.id),
                    'key': _folder_key(folder.id),
                    'value': folder.name,
                    'is_root': False,
                },
            },
        }

    @staticmethod
    def _asset_node(favorite, parent_key):
        info = FavoriteAssetSerializer(favorite).data['asset_info']
        return {
            **info,
            'pId': parent_key,
            'parent_key': parent_key,
        }

    def list(self, request, *args, **kwargs):
        parent_id = request.query_params.get('parent_id')
        folder_parent_id = None
        parent_key = FAVORITE_ROOT_ID
        include_root = not parent_id
        if parent_id and parent_id != FAVORITE_ROOT_ID:
            try:
                folder_parent_id = UUID(parent_id)
            except (TypeError, ValueError, AttributeError):
                return Response({'results': []})
            folder = FavoriteFolder.objects.filter(
                id=folder_parent_id, user=self.user,
            ).only('id').first()
            if folder is None:
                return Response({'results': []})
            parent_key = _folder_key(folder.id)

        folders = list(
            FavoriteFolder.objects.filter(
                user=self.user, parent_id=folder_parent_id,
            ).only('id', 'name', 'parent_id').order_by('name')
        )
        include_assets = is_true(
            request.query_params.get('include_assets', True)
        )
        favorites = []
        if include_assets:
            valid_assets = Asset.objects.all().valid().values('id')
            favorites = list(
                FavoriteAsset.objects.filter(
                    user=self.user,
                    folder_id=folder_parent_id,
                    asset_id__in=valid_assets,
                ).select_related('asset', 'asset__platform')
                .order_by('asset__name')
            )
        results = []
        if include_root:
            results.append({
                'id': FAVORITE_ROOT_ID,
                'name': 'Favorite',
                'title': 'Favorite',
                'pId': '',
                'open': True,
                'isParent': True,
                'hasChildren': True,
                'meta': {
                    'type': 'node',
                    'data': {
                        'id': FAVORITE_ROOT_ID,
                        'key': FAVORITE_ROOT_ID,
                        'value': 'Favorite',
                        'is_root': True,
                    },
                },
            })
        results.extend(self._folder_node(folder) for folder in folders)
        results.extend(
            self._asset_node(favorite, parent_key)
            for favorite in favorites
        )
        return Response({'results': results})


class UserAssetTreeMetricsApi(SelfOrPKUserMixin, CreateAPIView):
    serializer_class = serializers.UserAssetTreeMetricsQuerySerializer

    @property
    def self_rbac_perms(self):
        return (*super().self_rbac_perms, ('POST', 'perms.view_myassets'))

    @property
    def admin_rbac_perms(self):
        return (
            *super().admin_rbac_perms,
            ('POST', 'perms.view_userassets'),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        results = get_user_asset_tree_metrics(
            self.user, data['resources'], data['tree'],
        )
        return Response({'results': results})
