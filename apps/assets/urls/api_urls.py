# coding:utf-8
from django.urls import path
from .. import api
from rest_framework_bulk.routes import BulkRouter

app_name = 'assets'


router = BulkRouter()
router.register(r'assets', api.AssetViewSet, 'asset')
router.register(r'admin-user', api.AdminUserViewSet, 'admin-user')
router.register(r'system-user', api.SystemUserViewSet, 'system-user')
router.register(r'labels', api.LabelViewSet, 'label')
router.register(r'nodes', api.NodeViewSet, 'node')
router.register(r'domain', api.DomainViewSet, 'domain')
router.register(r'gateway', api.GatewayViewSet, 'gateway')

urlpatterns = [
    path('assets-bulk/', api.AssetListUpdateApi.as_view(), name='asset-bulk-update'),
    path('system-user/<uuid:pk>/auth-info/',
         api.SystemUserAuthInfoApi.as_view(), name='system-user-auth-info'),
    path('assets/<uuid:pk>/refresh/',
         api.AssetRefreshHardwareApi.as_view(), name='asset-refresh'),
    path('assets/<uuid:pk>/alive/',
         api.AssetAdminUserTestApi.as_view(), name='asset-alive-test'),
    path('assets/<uuid:pk>/gateway/',
         api.AssetGatewayApi.as_view(), name='asset-gateway'),
    path('admin-user/<uuid:pk>/nodes/',
         api.ReplaceNodesAdminUserApi.as_view(), name='replace-nodes-admin-user'),
    path('admin-user/<uuid:pk>/auth/',
         api.AdminUserAuthApi.as_view(), name='admin-user-auth'),
    path('admin-user/<uuid:pk>/connective/',
         api.AdminUserTestConnectiveApi.as_view(), name='admin-user-connective'),
    path('system-user/<uuid:pk>/push/',
         api.SystemUserPushApi.as_view(), name='system-user-push'),
    path('system-user/<uuid:pk>/connective/',
         api.SystemUserTestConnectiveApi.as_view(), name='system-user-connective'),
    path('nodes/<uuid:pk>/children/',
         api.NodeChildrenApi.as_view(), name='node-children'),
    path('nodes/children/', api.NodeChildrenApi.as_view(), name='node-children-2'),
    path('nodes/<uuid:pk>/children/add/',
         api.NodeAddChildrenApi.as_view(), name='node-add-children'),
    path('nodes/<uuid:pk>/assets/',
         api.NodeAssetsApi.as_view(), name='node-assets'),
    path('nodes/<uuid:pk>/assets/add/',
         api.NodeAddAssetsApi.as_view(), name='node-add-assets'),
    path('nodes/<uuid:pk>/assets/replace/',
         api.NodeReplaceAssetsApi.as_view(), name='node-replace-assets'),
    path('nodes/<uuid:pk>/assets/remove/',
         api.NodeRemoveAssetsApi.as_view(), name='node-remove-assets'),
    path('nodes/<uuid:pk>/refresh-hardware-info/',
         api.RefreshNodeHardwareInfoApi.as_view(), name='node-refresh-hardware-info'),
    path('nodes/<uuid:pk>/test-connective/',
         api.TestNodeConnectiveApi.as_view(), name='node-test-connective'),

    path('gateway/<uuid:pk>/test-connective/',
         api.GatewayTestConnectionApi.as_view(), name='test-gateway-connective'),
]

urlpatterns += router.urls

