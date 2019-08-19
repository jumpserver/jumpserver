# coding:utf-8

from django.urls import path, re_path
from .. import api_v2

app_name = 'perms'

urlpatterns = [
    # Assets

    path('users/<uuid:pk>/nodes/children/tree/', api_v2.UserGrantedNodeChildrenAsTreeApi.as_view(), name='user-nodes-children-as-tree'),

    # Nodes
    path('users/<uuid:pk>/nodes/children/', api_v2.UserGrantedNodesApi.as_view(), name='user-nodes'),
    path('users/<uuid:pk>/nodes/', api_v2.UserGrantedNodesApi.as_view(), name='user-nodes'),


    path('users/<uuid:pk>/assets/', api_v2.UserGrantedAssetApi.as_view(), name='user-assets'),
]
