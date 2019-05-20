# coding:utf-8
from django.urls import path
from rest_framework_nested import routers
# from rest_framework.routers import DefaultRouter
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'assets'

router = BulkRouter()
router.register(r'assets', api.AssetViewSet, 'asset')
router.register(r'admin-user', api.AdminUserViewSet, 'admin-user')
router.register(r'system-user', api.SystemUserViewSet, 'system-user')
router.register(r'labels', api.LabelViewSet, 'label')
router.register(r'nodes', api.NodeViewSet, 'node')
router.register(r'domain', api.DomainViewSet, 'domain')
router.register(r'gateway', api.GatewayViewSet, 'gateway')
router.register(r'cmd-filter', api.CommandFilterViewSet, 'cmd-filter')
router.register(r'asset-user', api.AssetUserViewSet, 'asset-user')

cmd_filter_router = routers.NestedDefaultRouter(router, r'cmd-filter', lookup='filter')
cmd_filter_router.register(r'rules', api.CommandFilterRuleViewSet, 'cmd-filter-rule')


urlpatterns = [
    path('assets-bulk/', api.AssetListUpdateApi.as_view(), name='asset-bulk-update'),
    path('asset/update/select/',
         api.AssetBulkUpdateSelectAPI.as_view(), name='asset-bulk-update-select'),
    path('assets/<uuid:pk>/refresh/',
         api.AssetRefreshHardwareApi.as_view(), name='asset-refresh'),
    path('assets/<uuid:pk>/alive/',
         api.AssetAdminUserTestApi.as_view(), name='asset-alive-test'),
    path('assets/<uuid:pk>/gateway/',
         api.AssetGatewayApi.as_view(), name='asset-gateway'),

    path('asset-user/auth-info/',
         api.AssetUserAuthInfoApi.as_view(), name='asset-user-auth-info'),
    path('asset-user/test-connective/',
         api.AssetUserTestConnectiveApi.as_view(), name='asset-user-connective'),


    path('admin-user/<uuid:pk>/nodes/',
         api.ReplaceNodesAdminUserApi.as_view(), name='replace-nodes-admin-user'),
    path('admin-user/<uuid:pk>/auth/',
         api.AdminUserAuthApi.as_view(), name='admin-user-auth'),
    path('admin-user/<uuid:pk>/connective/',
         api.AdminUserTestConnectiveApi.as_view(), name='admin-user-connective'),
    path('admin-user/<uuid:pk>/assets/',
         api.AdminUserAssetsListView.as_view(), name='admin-user-assets'),

    path('system-user/<uuid:pk>/auth-info/',
         api.SystemUserAuthInfoApi.as_view(), name='system-user-auth-info'),
    path('system-user/<uuid:pk>/asset/<uuid:aid>/auth-info/',
         api.SystemUserAssetAuthInfoApi.as_view(), name='system-user-asset-auth-info'),
    path('system-user/<uuid:pk>/assets/',
         api.SystemUserAssetsListView.as_view(), name='system-user-assets'),
    path('system-user/<uuid:pk>/push/',
         api.SystemUserPushApi.as_view(), name='system-user-push'),
    path('system-user/<uuid:pk>/asset/<uuid:aid>/push/',
         api.SystemUserPushToAssetApi.as_view(), name='system-user-push-to-asset'),
    path('system-user/<uuid:pk>/asset/<uuid:aid>/test/',
         api.SystemUserTestAssetConnectivityApi.as_view(), name='system-user-test-to-asset'),
    path('system-user/<uuid:pk>/connective/',
         api.SystemUserTestConnectiveApi.as_view(), name='system-user-connective'),
    path('system-user/<uuid:pk>/cmd-filter-rules/',
         api.SystemUserCommandFilterRuleListApi.as_view(), name='system-user-cmd-filter-rule-list'),

    path('nodes/tree/', api.NodeListAsTreeApi.as_view(), name='node-tree'),
    path('nodes/children/tree/', api.NodeChildrenAsTreeApi.as_view(), name='node-children-tree'),
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
    path('nodes/refresh-assets-amount/',
         api.RefreshAssetsAmount.as_view(), name='refresh-assets-amount'),

    path('gateway/<uuid:pk>/test-connective/',
         api.GatewayTestConnectionApi.as_view(), name='test-gateway-connective'),

]

urlpatterns += router.urls + cmd_filter_router.urls

