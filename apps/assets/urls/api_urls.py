# coding:utf-8
from django.urls import path
from rest_framework_bulk.routes import BulkRouter

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
router.register(r'accounts', api.AccountViewSet, 'account')
router.register(r'account-templates', api.AccountTemplateViewSet, 'account-template')
router.register(r'account-template-secrets', api.AccountTemplateSecretsViewSet, 'account-template-secret')
router.register(r'account-secrets', api.AccountSecretsViewSet, 'account-secret')
router.register(r'platforms', api.AssetPlatformViewSet, 'platform')
router.register(r'labels', api.LabelViewSet, 'label')
router.register(r'nodes', api.NodeViewSet, 'node')
router.register(r'domains', api.DomainViewSet, 'domain')
router.register(r'gateways', api.GatewayViewSet, 'gateway')
router.register(r'gathered-users', api.GatheredUserViewSet, 'gathered-user')
router.register(r'favorite-assets', api.FavoriteAssetViewSet, 'favorite-asset')
router.register(r'account-backup-plans', api.AccountBackupPlanViewSet, 'account-backup')
router.register(r'account-backup-plan-executions', api.AccountBackupPlanExecutionViewSet, 'account-backup-execution')

router.register(r'change-secret-automations', api.ChangeSecretAutomationViewSet, 'change-secret-automation')
router.register(r'change-secret-executions', api.ChangSecretExecutionViewSet, 'change-secret-execution')
router.register(r'gather-account-executions', api.GatherAccountsExecutionViewSet, 'gather-account-execution')
router.register(r'change-secret-records', api.ChangeSecretRecordViewSet, 'change-secret-record')
router.register(r'gather-account-automations', api.GatherAccountsAutomationViewSet, 'gather-account-automation')

urlpatterns = [
    # path('assets/<uuid:pk>/gateways/', api.AssetGatewayListApi.as_view(), name='asset-gateway-list'),
    path('assets/<uuid:pk>/tasks/', api.AssetTaskCreateApi.as_view(), name='asset-task-create'),
    path('assets/tasks/', api.AssetsTaskCreateApi.as_view(), name='assets-task-create'),
    path('assets/<uuid:pk>/perm-users/', api.AssetPermUserListApi.as_view(), name='asset-perm-user-list'),
    path('assets/<uuid:pk>/perm-users/<uuid:perm_user_id>/permissions/', api.AssetPermUserPermissionsListApi.as_view(),
         name='asset-perm-user-permission-list'),
    path('assets/<uuid:pk>/perm-user-groups/', api.AssetPermUserGroupListApi.as_view(),
         name='asset-perm-user-group-list'),
    path('assets/<uuid:pk>/perm-user-groups/<uuid:perm_user_group_id>/permissions/',
         api.AssetPermUserGroupPermissionsListApi.as_view(), name='asset-perm-user-group-permission-list'),

    path('accounts/tasks/', api.AccountTaskCreateAPI.as_view(), name='account-task-create'),
    path('account-secrets/<uuid:pk>/histories/', api.AccountHistoriesSecretAPI.as_view(),
         name='account-secret-history'),

    path('nodes/category/tree/', api.CategoryTreeApi.as_view(), name='asset-category-tree'),
    # path('nodes/tree/', api.NodeListAsTreeApi.as_view(), name='node-tree'),
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

    path('automation/<uuid:pk>/asset/remove/', api.AutomationRemoveAssetApi.as_view(), name='automation-remove-asset'),
    path('automation/<uuid:pk>/asset/add/', api.AutomationAddAssetApi.as_view(), name='automation-add-asset'),
    path('automation/<uuid:pk>/nodes/', api.AutomationNodeAddRemoveApi.as_view(), name='automation-add-or-remove-node'),
    path('automation/<uuid:pk>/assets/', api.AutomationAssetsListApi.as_view(), name='automation-assets'),
]

urlpatterns += router.urls
