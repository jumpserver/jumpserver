# coding:utf-8
from django.urls import path, re_path
from rest_framework_nested import routers
from rest_framework_bulk.routes import BulkRouter

from common import api as capi

from .. import api

app_name = 'assets'

router = BulkRouter()
router.register(r'assets', api.AssetViewSet, 'asset')
router.register(r'hosts', api.HostViewSet, 'host')
router.register(r'databases', api.DatabaseViewSet, 'database')
router.register(r'accounts', api.AccountViewSet, 'account')
router.register(r'account-secrets', api.AccountSecretsViewSet, 'account-secret')
router.register(r'accounts-history', api.AccountHistoryViewSet, 'account-history')
router.register(r'account-history-secrets', api.AccountHistorySecretsViewSet, 'account-history-secret')
router.register(r'platforms', api.AssetPlatformViewSet, 'platform')
router.register(r'labels', api.LabelViewSet, 'label')
router.register(r'nodes', api.NodeViewSet, 'node')
router.register(r'domains', api.DomainViewSet, 'domain')
router.register(r'gateways', api.GatewayViewSet, 'gateway')
router.register(r'gathered-users', api.GatheredUserViewSet, 'gathered-user')
router.register(r'favorite-assets', api.FavoriteAssetViewSet, 'favorite-asset')
router.register(r'account-backup-plans', api.AccountBackupPlanViewSet, 'account-backup')
router.register(r'account-backup-plan-executions', api.AccountBackupPlanExecutionViewSet, 'account-backup-execution')


urlpatterns = [
    # path('assets/<uuid:pk>/gateways/', api.AssetGatewayListApi.as_view(), name='asset-gateway-list'),
    path('assets/<uuid:pk>/tasks/', api.AssetTaskCreateApi.as_view(), name='asset-task-create'),
    path('assets/tasks/', api.AssetsTaskCreateApi.as_view(), name='assets-task-create'),
    path('assets/<uuid:pk>/perm-users/', api.AssetPermUserListApi.as_view(), name='asset-perm-user-list'),
    path('assets/<uuid:pk>/perm-users/<uuid:perm_user_id>/permissions/', api.AssetPermUserPermissionsListApi.as_view(), name='asset-perm-user-permission-list'),
    path('assets/<uuid:pk>/perm-user-groups/', api.AssetPermUserGroupListApi.as_view(), name='asset-perm-user-group-list'),
    path('assets/<uuid:pk>/perm-user-groups/<uuid:perm_user_group_id>/permissions/', api.AssetPermUserGroupPermissionsListApi.as_view(), name='asset-perm-user-group-permission-list'),

    path('accounts/tasks/', api.AccountTaskCreateAPI.as_view(), name='account-task-create'),

    path('nodes/category/tree/', api.CategoryTreeApi.as_view(), name='asset-category-tree'),
    path('nodes/tree/', api.NodeListAsTreeApi.as_view(), name='node-tree'),
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
]

urlpatterns += router.urls

