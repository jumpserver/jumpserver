from django.urls import path, include

from .. import api

user_permission_urlpatterns = [
    path('<str:user>/assets/<uuid:pk>/', api.UserPermedAssetRetrieveApi.as_view(), name='user-permed-asset'),
    path('<str:user>/assets/', api.UserAllPermedAssetsApi.as_view(), name='user-all-assets'),
    path('<str:user>/nodes/children/tree/', api.UserPermedAssetTreeAPI.as_view(), name='user-perm-node-children-tree'),
]

user_group_permission_urlpatterns = [
    path('<uuid:pk>/assets/', api.UserGroupGrantedAssetsApi.as_view(), name='user-group-assets'),
    path('<uuid:pk>/nodes/', api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes'),
    path('<uuid:pk>/nodes/children/', api.UserGroupGrantedNodesApi.as_view(), name='user-group-nodes-children'),
    path('<uuid:pk>/nodes/children/tree/', api.UserGroupGrantedNodeChildrenAsTreeApi.as_view(), name='user-group-nodes-children-as-tree'),
    path('<uuid:pk>/nodes/<uuid:node_id>/assets/', api.UserGroupGrantedNodeAssetsApi.as_view(), name='user-group-node-assets'),
]

user_permission_urlpatterns = [
    path('users/', include(user_permission_urlpatterns)),
    path('user-groups/', include(user_group_permission_urlpatterns)),
]
