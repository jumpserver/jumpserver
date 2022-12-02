from django.urls import path, include

from .. import api

user_permission_urlpatterns = [
    # <str:user> such as: my | self | user.id

    # assets
    path('<str:user>/assets/', api.UserAllPermedAssetsApi.as_view(),
         name='user-assets'),
    path('<str:user>/assets/tree/', api.UserDirectPermedAssetsAsTreeApi.as_view(),
         name='user-assets-as-tree'),
    path('<str:user>/ungroup/assets/tree/', api.UserUngroupAssetsAsTreeApi.as_view(),
         name='user-ungroup-assets-as-tree'),

    # nodes
    path('<str:user>/nodes/', api.UserGrantedNodesApi.as_view(),
         name='user-nodes'),
    path('<str:user>/nodes/tree/', api.UserGrantedNodesAsTreeApi.as_view(),
         name='user-nodes-as-tree'),
    path('<str:user>/nodes/children/', api.UserGrantedNodeChildrenApi.as_view(),
         name='user-nodes-children'),
    path('<str:user>/nodes/children/tree/', api.UserGrantedNodeChildrenAsTreeApi.as_view(),
         name='user-nodes-children-as-tree'),

    # node-assets
    path('<str:user>/nodes/<uuid:node_id>/assets/', api.UserPermedNodeAssetsApi.as_view(),
         name='user-node-assets'),
    path('<str:user>/nodes/ungrouped/assets/', api.UserDirectPermedAssetsApi.as_view(),
         name='user-ungrouped-assets'),
    path('<str:user>/nodes/favorite/assets/', api.UserFavoriteAssetsApi.as_view(),
         name='user-ungrouped-assets'),

    path('<str:user>/nodes/children-with-assets/tree/',
         api.UserGrantedNodeChildrenWithAssetsAsTreeApi.as_view(),
         name='user-nodes-children-with-assets-as-tree'),

    path('nodes-with-assets/tree/', api.MyGrantedNodesWithAssetsAsTreeApi.as_view(),
         name='my-nodes-with-assets-as-tree'),

    # accounts
    path('<str:user>/assets/<uuid:asset_id>/accounts/', api.UserPermedAssetAccountsApi.as_view(),
         name='user-permed-asset-accounts'),
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
