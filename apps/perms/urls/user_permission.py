from django.urls import path, include

from .. import api

user_permission_urlpatterns = [
    # <str:user> such as: my | self | user.id
    # assets
    path('<str:user>/assets/<uuid:pk>/', api.UserPermedAssetRetrieveApi.as_view(),
         name='user-permed-asset'),
    path('<str:user>/assets/', api.UserAllPermedAssetsApi.as_view(),
         name='user-all-assets'),

    path('<str:user>/nodes/ungrouped/assets/', api.UserDirectPermedAssetsApi.as_view(),
         name='user-direct-assets'),
    path('<str:user>/nodes/favorite/assets/', api.UserFavoriteAssetsApi.as_view(),
         name='user-favorite-assets'),
    path('<str:user>/nodes/<uuid:node_id>/assets/', api.UserPermedNodeAssetsApi.as_view(),
         name='user-node-assets'),

    # nodes
    path('<str:user>/nodes/', api.UserAllPermedNodesApi.as_view(),
         name='user-all-nodes'),
    path('<str:user>/nodes/children/', api.UserPermedNodeChildrenApi.as_view(),
         name='user-node-children'),

    # tree-asset
    path('<str:user>/assets/tree/', api.UserAllPermedAssetsAsTreeApi.as_view(),
         name='user-direct-assets-as-tree'),
    path('<str:user>/ungroup/assets/tree/', api.UserUngroupAssetsAsTreeApi.as_view(),
         name='user-ungroup-assets-as-tree'),

    # tree-node，不包含资产
    path('<str:user>/nodes/tree/', api.UserAllPermedNodesAsTreeApi.as_view(),
         name='user-all-nodes-as-tree'),
    path('<str:user>/nodes/children/tree/', api.UserPermedNodeChildrenAsTreeApi.as_view(),
         name='user-node-children-as-tree'),

    # tree-node-with-asset
    # 异步树
    path('<str:user>/nodes/children-with-assets/tree/',
         api.UserPermedNodeChildrenWithAssetsAsTreeApi.as_view(),
         name='user-node-children-with-assets-as-tree'),
    path('<str:user>/nodes/children-with-assets/category/tree/',
         api.UserPermedNodeChildrenWithAssetsAsCategoryTreeApi.as_view(),
         name='user-node-children-with-assets-as-category-tree'),
    # 同步树
    path('<str:user>/nodes/all-with-assets/tree/',
         api.UserPermedNodesWithAssetsAsTreeApi.as_view(),
         name='user-nodes-with-assets-as-tree'),
    path('<str:user>/nodes/children-with-k8s/tree/',
         api.UserGrantedK8sAsTreeApi.as_view(),
         name='user-nodes-children-with-k8s-as-tree'),
]

user_group_permission_urlpatterns = [
    # 查询某个用户组授权的资产和资产组
    path('<uuid:pk>/assets/', api.UserGroupGrantedAssetsApi.as_view(),
         name='user-group-assets'),
    path('<uuid:pk>/nodes/', api.UserGroupGrantedNodesApi.as_view(),
         name='user-group-nodes'),
    path('<uuid:pk>/nodes/children/', api.UserGroupGrantedNodesApi.as_view(),
         name='user-group-nodes-children'),
    path('<uuid:pk>/nodes/children/tree/', api.UserGroupGrantedNodeChildrenAsTreeApi.as_view(),
         name='user-group-nodes-children-as-tree'),
    path('<uuid:pk>/nodes/<uuid:node_id>/assets/', api.UserGroupGrantedNodeAssetsApi.as_view(),
         name='user-group-node-assets'),
]

user_permission_urlpatterns = [
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
]
