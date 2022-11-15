# coding:utf-8

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter

from .. import api

router = BulkRouter()
router.register('asset-permissions', api.AssetPermissionViewSet, 'asset-permission')
router.register('asset-permissions-users-relations', api.AssetPermissionUserRelationViewSet,
                'asset-permissions-users-relation')
router.register('asset-permissions-user-groups-relations', api.AssetPermissionUserGroupRelationViewSet,
                'asset-permissions-user-groups-relation')
router.register('asset-permissions-assets-relations', api.AssetPermissionAssetRelationViewSet,
                'asset-permissions-assets-relation')
router.register('asset-permissions-nodes-relations', api.AssetPermissionNodeRelationViewSet,
                'asset-permissions-nodes-relation')

permission_urlpatterns = [
    # 授权规则中授权的资产
    path('<uuid:pk>/assets/all/', api.AssetPermissionAllAssetListApi.as_view(), name='asset-permission-all-assets'),
    path('<uuid:pk>/users/all/', api.AssetPermissionAllUserListApi.as_view(), name='asset-permission-all-users'),
    path('<uuid:pk>/accounts/', api.AssetPermissionAccountListApi.as_view(), name='asset-permission-accounts'),
]

asset_permission_urlpatterns = [
    # Assets
    path('asset-permissions/', include(permission_urlpatterns)),
]

asset_permission_urlpatterns += router.urls
