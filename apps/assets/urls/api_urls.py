# coding:utf-8
from django.urls import path, re_path
from rest_framework_nested import routers
from rest_framework_bulk.routes import BulkRouter

from common import api as capi

from .. import api

app_name = 'assets'

router = BulkRouter()
router.register(r'assets', api.AssetViewSet, 'asset')
router.register(r'platforms', api.AssetPlatformViewSet, 'platform')
router.register(r'admin-users', api.AdminUserViewSet, 'admin-user')
router.register(r'system-users', api.SystemUserViewSet, 'system-user')
router.register(r'labels', api.LabelViewSet, 'label')
router.register(r'nodes', api.NodeViewSet, 'node')
router.register(r'domains', api.DomainViewSet, 'domain')
router.register(r'gateways', api.GatewayViewSet, 'gateway')
router.register(r'cmd-filters', api.CommandFilterViewSet, 'cmd-filter')
router.register(r'asset-users', api.AssetUserViewSet, 'asset-user')
router.register(r'asset-user-auth-infos', api.AssetUserAuthInfoViewSet, 'asset-user-auth-info')
router.register(r'gathered-users', api.GatheredUserViewSet, 'gathered-user')
router.register(r'favorite-assets', api.FavoriteAssetViewSet, 'favorite-asset')
router.register(r'system-users-assets-relations', api.SystemUserAssetRelationViewSet, 'system-users-assets-relation')
router.register(r'system-users-nodes-relations', api.SystemUserNodeRelationViewSet, 'system-users-nodes-relation')
router.register(r'system-users-users-relations', api.SystemUserUserRelationViewSet, 'system-users-users-relation')

cmd_filter_router = routers.NestedDefaultRouter(router, r'cmd-filters', lookup='filter')
cmd_filter_router.register(r'rules', api.CommandFilterRuleViewSet, 'cmd-filter-rule')


urlpatterns = [
    path('assets/<uuid:pk>/gateways/', api.AssetGatewayListApi.as_view(), name='asset-gateway-list'),
    path('assets/<uuid:pk>/platform/', api.AssetPlatformRetrieveApi.as_view(), name='asset-platform-detail'),
    path('assets/<uuid:pk>/tasks/', api.AssetTaskCreateApi.as_view(), name='asset-task-create'),
    path('assets/tasks/', api.AssetsTaskCreateApi.as_view(), name='assets-task-create'),

    path('asset-users/tasks/', api.AssetUserTaskCreateAPI.as_view(), name='asset-user-task-create'),

    path('admin-users/<uuid:pk>/nodes/', api.ReplaceNodesAdminUserApi.as_view(), name='replace-nodes-admin-user'),
    path('admin-users/<uuid:pk>/auth/', api.AdminUserAuthApi.as_view(), name='admin-user-auth'),
    path('admin-users/<uuid:pk>/connective/', api.AdminUserTestConnectiveApi.as_view(), name='admin-user-connective'),
    path('admin-users/<uuid:pk>/assets/', api.AdminUserAssetsListView.as_view(), name='admin-user-assets'),

    path('system-users/<uuid:pk>/auth-info/', api.SystemUserAuthInfoApi.as_view(), name='system-user-auth-info'),
    path('system-users/<uuid:pk>/assets/', api.SystemUserAssetsListView.as_view(), name='system-user-assets'),
    path('system-users/<uuid:pk>/assets/<uuid:aid>/auth-info/', api.SystemUserAssetAuthInfoApi.as_view(), name='system-user-asset-auth-info'),
    path('system-users/<uuid:pk>/tasks/', api.SystemUserTaskApi.as_view(), name='system-user-task-create'),
    path('system-users/<uuid:pk>/cmd-filter-rules/', api.SystemUserCommandFilterRuleListApi.as_view(), name='system-user-cmd-filter-rule-list'),

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

old_version_urlpatterns = [
    re_path('(?P<resource>admin-user|system-user|domain|gateway|cmd-filter|asset-user)/.*', capi.redirect_plural_name_api)
]

urlpatterns += router.urls + cmd_filter_router.urls + old_version_urlpatterns

