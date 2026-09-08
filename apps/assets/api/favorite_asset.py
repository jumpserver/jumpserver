# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_bulk.generics import BulkModelViewSet

from common.permissions import IsValidUser
from orgs.utils import tmp_to_org, tmp_to_root_org
from ..models import Asset, FavoriteAsset, FavoriteFolder
from ..serializers import (
    FavoriteAssetSerializer, FavoriteAssetsToFolderSerializer,
    FavoriteFolderSerializer,
)

__all__ = ['FavoriteAssetViewSet', 'FavoriteFolderViewSet']

FAVORITE_ASSET_BATCH_SIZE = 1000


def _chunked(items, size=FAVORITE_ASSET_BATCH_SIZE):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _collect_descendant_folder_ids(folder_id, folder_relations):
    children_by_parent = defaultdict(list)
    for child_id, parent_id in folder_relations:
        children_by_parent[parent_id].append(child_id)

    descendant_ids = set()
    pending = [folder_id]
    while pending:
        current_id = pending.pop()
        if current_id in descendant_ids:
            continue
        descendant_ids.add(current_id)
        pending.extend(children_by_parent.get(current_id, ()))
    return descendant_ids


def _move_assets_to_folder(user, folder, asset_ids):
    operator = user.name
    target_folder_id = getattr(folder, 'id', None)
    with transaction.atomic():
        for asset_id_batch in _chunked(asset_ids):
            existing_rows = list(
                FavoriteAsset.objects.select_for_update()
                .filter(user=user, asset_id__in=asset_id_batch)
                .order_by('-date_updated', '-date_created', 'id')
                .values_list('id', 'asset_id', 'folder_id')
            )
            retained_by_asset = {}
            duplicate_ids = []
            for favorite_id, asset_id, folder_id in existing_rows:
                retained = retained_by_asset.get(asset_id)
                if retained is None:
                    retained_by_asset[asset_id] = (favorite_id, folder_id)
                    continue
                retained_id, retained_folder_id = retained
                if (
                    folder_id == target_folder_id and
                    retained_folder_id != target_folder_id
                ):
                    duplicate_ids.append(retained_id)
                    retained_by_asset[asset_id] = (favorite_id, folder_id)
                else:
                    duplicate_ids.append(favorite_id)

            if duplicate_ids:
                FavoriteAsset.objects.filter(id__in=duplicate_ids).delete()

            retained_ids = [item[0] for item in retained_by_asset.values()]
            if retained_ids:
                FavoriteAsset.objects.filter(id__in=retained_ids).update(
                    folder=folder, updated_by=operator
                )

            missing_asset_ids = [
                asset_id
                for asset_id in asset_id_batch
                if asset_id not in retained_by_asset
            ]
            if not missing_asset_ids:
                continue
            FavoriteAsset.objects.bulk_create(
                [
                    FavoriteAsset(
                        user=user,
                        asset_id=asset_id,
                        folder=folder,
                        created_by=operator,
                        updated_by=operator,
                    )
                    for asset_id in missing_asset_ids
                ],
                batch_size=FAVORITE_ASSET_BATCH_SIZE,
                ignore_conflicts=True,
            )


def _validate_permitted_assets(user, asset_ids):
    from perms.utils import UserPermAssetUtil

    asset_ids_by_org = defaultdict(list)
    for asset_id_batch in _chunked(asset_ids):
        for org_id, asset_id in Asset.objects.filter(
            id__in=asset_id_batch
        ).values_list('org_id', 'id'):
            asset_ids_by_org[org_id].append(asset_id)

    permitted_ids = set()
    for org_id, org_asset_ids in asset_ids_by_org.items():
        with tmp_to_org(org_id):
            asset_util = UserPermAssetUtil(user)
            for asset_id_batch in _chunked(org_asset_ids):
                permitted_ids.update(
                    asset_util.get_all_assets()
                    .filter(id__in=asset_id_batch)
                    .values_list('id', flat=True)
                )
    invalid_ids = [
        asset_id for asset_id in asset_ids
        if asset_id not in permitted_ids
    ]
    if invalid_ids:
        raise ValidationError({
            'assets': _('Some assets are not authorized for this user.')
        })


class FavoriteFolderViewSet(BulkModelViewSet):
    serializer_class = FavoriteFolderSerializer
    permission_classes = (IsValidUser,)
    page_no_limit = True

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return FavoriteFolder.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        folder_relations = FavoriteFolder.objects.filter(
            user_id=instance.user_id
        ).values_list('id', 'parent_id')
        subtree_ids = _collect_descendant_folder_ids(
            instance.id, folder_relations
        )
        if FavoriteAsset.objects.filter(folder_id__in=subtree_ids).exists():
            raise ValidationError({
                'detail': _('Deletion failed and the node contains assets')
            })
        instance.delete()

    @action(methods=['post'], detail=True, url_path='assets')
    def add_assets(self, request, *args, **kwargs):
        folder = self.get_object()
        input_serializer = FavoriteAssetsToFolderSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        asset_ids = input_serializer.validated_data['assets']

        _validate_permitted_assets(request.user, asset_ids)
        _move_assets_to_folder(request.user, folder, asset_ids)

        return Response({'count': len(asset_ids)}, status=status.HTTP_200_OK)


class FavoriteAssetViewSet(BulkModelViewSet):
    queryset = FavoriteAsset.objects.none()
    serializer_class = FavoriteAssetSerializer
    permission_classes = (IsValidUser,)
    filterset_fields = ['asset', 'folder']
    page_no_limit = True

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().dispatch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        asset_id = request.data.get('asset')
        folder_id = request.data.get('folder')
        queryset = FavoriteAsset.objects.filter(
            user=request.user, asset_id=asset_id
        )
        instance = (
            queryset.filter(folder_id=folder_id).first() or queryset.first()
        )

        if instance:
            serializer = self.get_serializer(instance, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        asset = serializer.validated_data.get('asset')
        folder = serializer.validated_data.get('folder')
        if instance:
            asset = asset or instance.asset
            if 'folder' not in serializer.validated_data:
                folder = instance.folder
        _move_assets_to_folder(request.user, folder, [asset.id])
        favorite = FavoriteAsset.objects.get(user=request.user, asset=asset)
        output_serializer = self.get_serializer(favorite)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['post', 'delete'], detail=False, url_path='batch')
    def batch(self, request, *args, **kwargs):
        input_serializer = FavoriteAssetsToFolderSerializer(
            data=request.data, context={'request': request}
        )
        input_serializer.is_valid(raise_exception=True)
        asset_ids = input_serializer.validated_data['assets']
        if request.method == 'DELETE':
            favorites = FavoriteAsset.objects.filter(
                user=request.user, asset_id__in=asset_ids
            )
            count = favorites.count()
            favorites.delete()
            return Response({'count': count}, status=status.HTTP_200_OK)

        folder = input_serializer.validated_data['folder']
        _validate_permitted_assets(request.user, asset_ids)
        _move_assets_to_folder(request.user, folder, asset_ids)
        return Response({'count': len(asset_ids)}, status=status.HTTP_200_OK)

    def get_queryset(self):
        queryset = FavoriteAsset.objects.filter(
            user=self.request.user
        ).select_related('asset', 'asset__platform')
        return queryset

    def allow_bulk_destroy(self, qs, filtered):
        return filtered.count() == 1
