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
    # 统一说明：
    # `<uuid:pk>`: `User.pk`
    # 直接授权：在 `AssetPermission` 中关联的对象

    # ---------------------------------------------------------
    # 以 serializer 格式返回
    path('<uuid:pk>/assets/', api.UserAllGrantedAssetsApi.as_view(), name='user-assets'),
    path('assets/', api.MyAllGrantedAssetsApi.as_view(), name='my-assets'),

    # Tree Node 的数据格式返回
    path('<uuid:pk>/assets/tree/', api.UserDirectGrantedAssetsAsTreeForAdminApi.as_view(), name='user-assets-as-tree'),
    path('assets/tree/', api.MyAllAssetsAsTreeApi.as_view(), name='my-assets-as-tree'),
    path('ungroup/assets/tree/', api.MyUngroupAssetsAsTreeApi.as_view(), name='my-ungroup-assets-as-tree'),
    # ^--------------------------------------------------------^

    # 获取用户所有`直接授权的节点`与`直接授权资产`关联的节点
    # 以 serializer 格式返回
    path('<uuid:pk>/nodes/', api.UserGrantedNodesForAdminApi.as_view(), name='user-nodes'),
    path('nodes/', api.MyGrantedNodesApi.as_view(), name='my-nodes'),

    # 以 Tree Node 的数据格式返回
    path('<uuid:pk>/nodes/tree/', api.MyGrantedNodesAsTreeApi.as_view(), name='user-nodes-as-tree'),
    path('nodes/tree/', api.MyGrantedNodesAsTreeApi.as_view(), name='my-nodes-as-tree'),
    # ^--------------------------------------------------------^

    # 一层一层的获取用户授权的节点，
    # 以 Serializer 的数据格式返回
    path('<uuid:pk>/nodes/children/', api.UserGrantedNodeChildrenForAdminApi.as_view(), name='user-nodes-children'),
    path('nodes/children/', api.MyGrantedNodeChildrenApi.as_view(), name='my-nodes-children'),

    # 以 Tree Node 的数据格式返回
    path('<uuid:pk>/nodes/children/tree/', api.UserGrantedNodeChildrenAsTreeForAdminApi.as_view(), name='user-nodes-children-as-tree'),
    # 部分调用位置
    # - 普通用户 -> 我的资产 -> 展开节点 时调用
    path('nodes/children/tree/', api.MyGrantedNodeChildrenAsTreeApi.as_view(), name='my-nodes-children-as-tree'),
    # ^--------------------------------------------------------^

    # 此接口会返回整棵树
    # 普通用户 -> 命令执行 -> 左侧树
    path('nodes-with-assets/tree/', api.MyGrantedNodesWithAssetsAsTreeApi.as_view(), name='my-nodes-with-assets-as-tree'),

    # 主要用于 luna 页面，带资产的节点树
    path('<uuid:pk>/nodes/children-with-assets/tree/', api.UserGrantedNodeChildrenWithAssetsAsTreeApi.as_view(), name='user-nodes-children-with-assets-as-tree'),
    path('nodes/children-with-assets/tree/', api.MyGrantedNodeChildrenWithAssetsAsTreeApi.as_view(), name='my-nodes-children-with-assets-as-tree'),

    # 查询授权树上某个节点的所有资产
    path('<uuid:pk>/nodes/<uuid:node_id>/assets/', api.UserGrantedNodeAssetsForAdminApi.as_view(), name='user-node-assets'),
    path('nodes/<uuid:node_id>/assets/', api.MyGrantedNodeAssetsApi.as_view(), name='my-node-assets'),

    # 未分组的资产
    path('<uuid:pk>/nodes/ungrouped/assets/', api.UserDirectGrantedAssetsForAdminApi.as_view(), name='user-ungrouped-assets'),
    path('nodes/ungrouped/assets/', api.MyDirectGrantedAssetsApi.as_view(), name='my-ungrouped-assets'),

    # 收藏的资产
    path('<uuid:pk>/nodes/favorite/assets/', api.UserFavoriteGrantedAssetsForAdminApi.as_view(), name='user-ungrouped-assets'),
    path('nodes/favorite/assets/', api.MyFavoriteGrantedAssetsApi.as_view(), name='my-ungrouped-assets'),

    # Asset System users
    path('<uuid:pk>/assets/<uuid:asset_id>/system-users/', api.UserGrantedAssetSystemUsersForAdminApi.as_view(), name='user-asset-system-users'),
    path('assets/<uuid:asset_id>/system-users/', api.MyGrantedAssetSystemUsersApi.as_view(), name='my-asset-system-users'),

    # TODO 要废弃 Expire user permission cache
    path('<uuid:pk>/asset-permissions/cache/', api.UserAssetPermissionsCacheApi.as_view(),
         name='user-asset-permission-cache'),
    path('asset-permissions/cache/', api.UserAssetPermissionsCacheApi.as_view(), name='my-asset-permission-cache'),
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
