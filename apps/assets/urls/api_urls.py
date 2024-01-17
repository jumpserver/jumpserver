# coding:utf-8
from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from labels.api import LabelViewSet
from .. import api

app_name = 'assets'

router = BulkRouter()
router.register(r'categories', api.CategoryViewSet, 'category')
router.register(r'assets', api.AssetViewSet, 'asset')
router.register(r'hosts', api.HostViewSet, 'host')
router.register(r'devices', api.DeviceViewSet, 'device')
router.register(r'databases', api.DatabaseViewSet, 'database')
router.register(r'webs', api.WebViewSet, 'web')
router.register(r'clouds', api.CloudViewSet, 'cloud')
router.register(r'gpts', api.GPTViewSet, 'gpt')
router.register(r'customs', api.CustomViewSet, 'custom')
router.register(r'platforms', api.AssetPlatformViewSet, 'platform')
router.register(r'nodes', api.NodeViewSet, 'node')
router.register(r'domains', api.DomainViewSet, 'domain')
router.register(r'gateways', api.GatewayViewSet, 'gateway')
router.register(r'favorite-assets', api.FavoriteAssetViewSet, 'favorite-asset')
router.register(r'protocol-settings', api.PlatformProtocolViewSet, 'protocol-setting')
router.register(r'labels', LabelViewSet, 'label')

urlpatterns = [
    # path('assets/<uuid:pk>/gateways/', api.AssetGatewayListApi.as_view(), name='asset-gateway-list'),
    path('protocols/', api.ProtocolListApi.as_view(), name='asset-protocol'),
    path('assets/<uuid:pk>/tasks/', api.AssetTaskCreateApi.as_view(), name='asset-task-create'),
    path('assets/tasks/', api.AssetsTaskCreateApi.as_view(), name='assets-task-create'),
    path('assets/<uuid:pk>/perm-users/', api.AssetPermUserListApi.as_view(), name='asset-perm-user-list'),
    path('assets/<uuid:pk>/perm-users/<uuid:perm_user_id>/permissions/', api.AssetPermUserPermissionsListApi.as_view(),
         name='asset-perm-user-permission-list'),
    path('assets/<uuid:pk>/perm-user-groups/', api.AssetPermUserGroupListApi.as_view(),
         name='asset-perm-user-group-list'),
    path('assets/<uuid:pk>/perm-user-groups/<uuid:perm_user_group_id>/permissions/',
         api.AssetPermUserGroupPermissionsListApi.as_view(), name='asset-perm-user-group-permission-list'),

    path('nodes/category/tree/', api.CategoryTreeApi.as_view(), name='asset-category-tree'),
    path('nodes/children/tree/', api.NodeChildrenAsTreeApi.as_view(), name='node-children-tree'),
    path('nodes/<uuid:pk>/children/', api.NodeChildrenApi.as_view(), name='node-children'),
    path('nodes/children/', api.NodeChildrenApi.as_view(), name='node-children-2'),
    path('nodes/<uuid:pk>/children/add/', api.NodeAddChildrenApi.as_view(), name='node-add-children'),
    path('nodes/<uuid:pk>/assets/', api.NodeAssetsApi.as_view(), name='node-assets'),
    path('nodes/<uuid:pk>/assets/add/', api.NodeAddAssetsApi.as_view(), name='node-add-assets'),
    path('nodes/<uuid:pk>/assets/replace/', api.MoveAssetsToNodeApi.as_view(), name='node-replace-assets'),
    path('nodes/<uuid:pk>/assets/remove/', api.NodeRemoveAssetsApi.as_view(), name='node-remove-assets'),
    path('nodes/<uuid:pk>/tasks/', api.NodeTaskCreateApi.as_view(), name='node-task-create'),

    path('gateways/<uuid:pk>/test-connective/', api.GatewayTestConnectionApi.as_view(), name='test-gateway-connective'),
    path('platform-automation-methods/', api.PlatformAutomationMethodsApi.as_view(),
         name='platform-automation-methods'),
]

urlpatterns += router.urls
