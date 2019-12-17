# coding:utf-8

from django.urls import path, include
from rest_framework_bulk.routes import BulkRouter
from .. import api

router = BulkRouter()
router.register('asset-permissions', api.AssetPermissionViewSet, 'asset-permission')
router.register('asset-permissions-users-relations', api.AssetPermissionUserRelationViewSet, 'asset-permissions-users-relation')
router.register('asset-permissions-user-groups-relations', api.AssetPermissionUserGroupRelationViewSet, 'asset-permissions-user-groups-relation')
router.register('asset-permissions-assets-relations', api.AssetPermissionAssetRelationViewSet, 'asset-permissions-assets-relation')
router.register('asset-permissions-nodes-relations', api.AssetPermissionNodeRelationViewSet, 'asset-permissions-nodes-relation')
router.register('asset-permissions-system-users-relations', api.AssetPermissionSystemUserRelationViewSet, 'asset-permissions-system-users-relation')

user_permission_urlpatterns = [
    path('<uuid:pk>/assets/', api.UserGrantedAssetsApi.as_view(), name='user-assets'),
    path('assets/', api.UserGrantedAssetsApi.as_view(), name='my-assets'),

    # Assets as tree
    path('<uuid:pk>/assets/tree/', api.UserGrantedAssetsAsTreeApi.as_view(), name='user-assets-as-tree'),
    path('assets/tree/', api.UserGrantedAssetsAsTreeApi.as_view(), name='my-assets-as-tree'),

    # Nodes
    path('<uuid:pk>/nodes/', api.UserGrantedNodesApi.as_view(), name='user-nodes'),
    path('nodes/', api.UserGrantedNodesApi.as_view(), name='my-nodes'),

    # Node children
    path('<uuid:pk>/nodes/children/', api.UserGrantedNodesApi.as_view(), name='user-nodes-children'),
    path('nodes/children/', api.UserGrantedNodesApi.as_view(), name='my-nodes-children'),

    # Node as tree
    path('<uuid:pk>/nodes/tree/', api.UserGrantedNodesAsTreeApi.as_view(), name='user-nodes-as-tree'),
    path('nodes/tree/', api.UserGrantedNodesAsTreeApi.as_view(), name='my-nodes-as-tree'),

    # Node with assets as tree
    path('<uuid:pk>/nodes-with-assets/tree/', api.UserGrantedNodesWithAssetsAsTreeApi.as_view(), name='user-nodes-with-assets-as-tree'),
    path('nodes-with-assets/tree/', api.UserGrantedNodesWithAssetsAsTreeApi.as_view(), name='my-nodes-with-assets-as-tree'),

    # Node children as tree
    path('<uuid:pk>/nodes/children/tree/', api.UserGrantedNodeChildrenAsTreeApi.as_view(), name='user-nodes-children-as-tree'),
    path('nodes/children/tree/', api.UserGrantedNodeChildrenAsTreeApi.as_view(), name='my-nodes-children-as-tree'),

    # Node children with assets as tree
    path('<uuid:pk>/nodes/children-with-assets/tree/', api.UserGrantedNodeChildrenWithAssetsAsTreeApi.as_view(), name='user-nodes-children-with-assets-as-tree'),
    path('nodes/children-with-assets/tree/', api.UserGrantedNodeChildrenWithAssetsAsTreeApi.as_view(), name='my-nodes-children-with-assets-as-tree'),

    # Node assets
    path('<uuid:pk>/nodes/<uuid:node_id>/assets/', api.UserGrantedNodeAssetsApi.as_view(), name='user-node-assets'),
    path('nodes/<uuid:node_id>/assets/', api.UserGrantedNodeAssetsApi.as_view(), name='my-node-assets'),

    # Asset System users
    path('users/<uuid:pk>/assets/<uuid:asset_id>/system-users/', api.UserGrantedAssetSystemUsersApi.as_view(), name='user-asset-system-users'),
    path('assets/<uuid:asset_id>/system-users/', api.UserGrantedAssetSystemUsersApi.as_view(), name='my-asset-system-users'),
]

user_group_permission_urlpatterns = [
    # 查询某个用户组授权的资产和资产组
    path('<uuid:pk>/assets/', api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    path('<uuid:pk>/nodes/', api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes'),
    path('<uuid:pk>/nodes/children/', api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes-children'),
    path('<uuid:pk>/nodes/children/tree/', api.UserGroupGrantedNodeChildrenAsTreeApi.as_view(), name='user-group-nodes-children-as-tree'),
    path('<uuid:pk>/nodes/<uuid:node_id>/assets/', api.UserGroupGrantedNodeAssetsApi.as_view(), name='user-group-node-assets'),
    path('<uuid:pk>/assets/<uuid:asset_id>/system-users/', api.UserGroupGrantedAssetSystemUsersApi.as_view(), name='user-group-asset-system-users'),
]

permission_urlpatterns = [
    # 授权规则中授权的资产
    path('<uuid:pk>/assets/all/', api.AssetPermissionAllAssetListApi.as_view(), name='asset-permission-all-assets'),
    path('<uuid:pk>/users/all/', api.AssetPermissionAllUserListApi.as_view(), name='asset-permission-all-users'),

    # 验证用户是否有某个资产和系统用户的权限
    path('user/validate/', api.ValidateUserAssetPermissionApi.as_view(), name='validate-user-asset-permission'),
    path('user/actions/', api.GetUserAssetPermissionActionsApi.as_view(), name='get-user-asset-permission-actions'),

    # 刷新缓存
    path('cache/refresh/', api.RefreshAssetPermissionCacheApi.as_view(), name='refresh-asset-permission-cache'),
]

asset_permission_urlpatterns = [
    # Assets
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
    path('asset-permissions/', include(permission_urlpatterns)),
]

asset_permission_urlpatterns += router.urls
