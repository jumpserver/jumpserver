# coding:utf-8

from django.urls import path, re_path
from .. import api_v2

app_name = 'perms'

urlpatterns = [
    # Assets
    path('users/<uuid:pk>/nodes/children/tree/', api_v2.UserGrantedNodeChildrenAsTreeApi.as_view(), name='user-nodes-children-as-tree'),

    # Nodes
    path('users/<uuid:pk>/nodes/children/', api_v2.UserGrantedNodesApi.as_view(), name='user-nodes'),
    path('users/<uuid:pk>/nodes/<uuid:node_id>/assets/', api_v2.UserGrantedNodeAssetsApi.as_view(), name='user-node-assets'),
    path('users/<uuid:pk>/nodes/', api_v2.UserGrantedNodesApi.as_view(), name='user-nodes'),

    path('users/<uuid:pk>/assets/', api_v2.UserGrantedAssetsApi.as_view(), name='user-assets'),
    path('users/<uuid:pk>/assets/<uuid:asset_id>/system-users/', api_v2.UserGrantedAssetSystemUsersApi.as_view(), name='user-asset-system-users'),
]
