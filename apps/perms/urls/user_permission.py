from django.urls import path, include

from .. import api

user_permission_urlpatterns = [
    path(
        '<str:user>/assets/<uuid:pk>/', 
        api.UserPermedAssetRetrieveApi.as_view(), 
        name='user-permed-asset'),
    path(
        '<str:user>/assets/', 
        api.UserAllPermedAssetsApi.as_view(),
        name='user-all-assets'),
    path(
        '<str:user>/nodes/ungrouped/assets/', 
        api.UserDirectPermedAssetsApi.as_view(), 
        name='user-direct-assets'),
    path(
        '<str:user>/nodes/favorite/assets/', 
        api.UserFavoriteAssetsApi.as_view(), 
        name='user-favorite-assets'),
    path(
        '<str:user>/nodes/<uuid:node_id>/assets/', 
        api.UserPermedNodeAssetsApi.as_view(), 
        name='user-node-assets'),

    # nodes
    path(
        '<str:user>/nodes/', 
        api.UserAllPermedNodesApi.as_view(), 
        name='user-all-nodes'),
    path(
        '<str:user>/nodes/children/', 
        api.UserPermedNodeChildrenApi.as_view(), 
        name='user-node-children'),

    path(
        '<str:user>/assets/tree/', 
        api.UserAllPermedAssetsAsTreeApi.as_view(), 
        name='user-direct-assets-as-tree'),
    path(
        '<str:user>/ungroup/assets/tree/', 
        api.UserUngroupAssetsAsTreeApi.as_view(), 
        name='user-ungroup-assets-as-tree'),

    # - 资产节点同步树 - #
    path(
        '<str:user>/nodes/all-with-assets/tree/', 
        api.UserAssetNodeTreeSyncApi.as_view(),
        name='user-nodes-with-assets-as-tree'),

    # - 资产节点异步树 - #
    # 资产节点树(不包含资产)
    path(
        '<str:user>/nodes/tree/', 
        api.UserAssetNodeTreeApi.as_view(with_assets=False), 
        name='user-all-nodes-as-tree'),
    # 资产节点树(展开节点)(不包含资产)
    path(
        '<str:user>/nodes/children/tree/', 
        api.UserAssetNodeTreeApi.as_view(with_assets=False), 
        name='user-node-children-as-tree'),

    # * 资产节点树(包含资产)(包含展开节点)(包含搜索资产和节点)
    path(
        '<str:user>/nodes/children-with-assets/tree/', 
        api.UserAssetNodeTreeApi.as_view(with_assets=True), 
        name='user-node-children-with-assets-as-tree'),
    
    # - 资产类型同步树 - #
    path(
        '<str:user>/nodes/children-with-assets/category/tree/sync/', 
        api.UserAssetTypeTreeSyncApi.as_view(with_assets=True),
        name='user-node-children-with-assets-as-category-tree'),

    # - 资产类型异步树 - #
    # 资产类型树(包含资产)(包含展开节点)
    path(
        '<str:user>/nodes/children-with-assets/category/tree/', 
        api.UserAssetTypeTreeApi.as_view(with_assets=True),
        name='user-node-children-with-assets-as-category-tree'),
]

user_group_permission_urlpatterns = [
    # 查询某个用户组授权的资产和资产组
    path(
        '<uuid:pk>/assets/', 
        api.UserGroupGrantedAssetsApi.as_view(), 
        name='user-group-assets'),
    path(
        '<uuid:pk>/nodes/', 
        api.UserGroupGrantedNodesApi.as_view(), 
        name='user-group-nodes'),
    path(
        '<uuid:pk>/nodes/children/', 
        api.UserGroupGrantedNodesApi.as_view(), 
        name='user-group-nodes-children'),
    path(
        '<uuid:pk>/nodes/children/tree/', 
        api.UserGroupGrantedNodeChildrenAsTreeApi.as_view(), 
        name='user-group-nodes-children-as-tree'),
    path(
        '<uuid:pk>/nodes/<uuid:node_id>/assets/', 
        api.UserGroupGrantedNodeAssetsApi.as_view(), 
        name='user-group-node-assets'),
]

user_permission_urlpatterns = [
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
]
