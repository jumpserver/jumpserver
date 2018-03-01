# coding:utf-8
from django.conf.urls import url
from .. import api
from rest_framework_bulk.routes import BulkRouter

app_name = 'assets'


router = BulkRouter()
# router.register(r'v1/groups', api.AssetGroupViewSet, 'asset-group')
router.register(r'v1/assets', api.AssetViewSet, 'asset')
# router.register(r'v1/clusters', api.ClusterViewSet, 'cluster')
router.register(r'v1/admin-user', api.AdminUserViewSet, 'admin-user')
router.register(r'v1/system-user', api.SystemUserViewSet, 'system-user')
router.register(r'v1/labels', api.LabelViewSet, 'label')
router.register(r'v1/nodes', api.NodeViewSet, 'node')

urlpatterns = [
    url(r'^v1/assets-bulk/$', api.AssetListUpdateApi.as_view(), name='asset-bulk-update'),
    url(r'^v1/system-user/(?P<pk>[0-9a-zA-Z\-]{36})/auth-info/', api.SystemUserAuthInfoApi.as_view(),
        name='system-user-auth-info'),
    url(r'^v1/assets/(?P<pk>[0-9a-zA-Z\-]{36})/refresh/$',
        api.AssetRefreshHardwareApi.as_view(), name='asset-refresh'),
    url(r'^v1/assets/(?P<pk>[0-9a-zA-Z\-]{36})/alive/$',
        api.AssetAdminUserTestApi.as_view(), name='asset-alive-test'),
    url(r'^v1/assets/user-assets/$',
        api.UserAssetListView.as_view(), name='user-asset-list'),
    # update the asset group, which add or delete the asset to the group
    #url(r'^v1/groups/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$',
    #    api.GroupUpdateAssetsApi.as_view(), name='group-update-assets'),
    #url(r'^v1/groups/(?P<pk>[0-9a-zA-Z\-]{36})/assets/add/$',
    #    api.GroupAddAssetsApi.as_view(), name='group-add-assets'),
    # update the Cluster, and add or delete the assets to the Cluster
    #url(r'^v1/cluster/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$',
    #    api.ClusterAddAssetsApi.as_view(), name='cluster-add-assets'),
    #url(r'^v1/cluster/(?P<pk>[0-9a-zA-Z\-]{36})/assets/connective/$',
    #    api.ClusterTestAssetsAliveApi.as_view(), name='cluster-test-connective'),
    url(r'^v1/admin-user/(?P<pk>[0-9a-zA-Z\-]{36})/nodes/$',
        api.ReplaceNodesAdminUserApi.as_view(), name='replace-nodes-admin-user'),
    url(r'^v1/admin-user/(?P<pk>[0-9a-zA-Z\-]{36})/connective/$',
        api.AdminUserTestConnectiveApi.as_view(), name='admin-user-connective'),
    url(r'^v1/system-user/(?P<pk>[0-9a-zA-Z\-]{36})/push/$',
        api.SystemUserPushApi.as_view(), name='system-user-push'),
    url(r'^v1/system-user/(?P<pk>[0-9a-zA-Z\-]{36})/connective/$',
        api.SystemUserTestConnectiveApi.as_view(), name='system-user-connective'),
    url(r'^v1/nodes/(?P<pk>[0-9a-zA-Z\-]{36})/children/$', api.NodeChildrenApi.as_view(), name='node-children'),
    url(r'^v1/nodes/(?P<pk>[0-9a-zA-Z\-]{36})/children/add/$', api.NodeAddChildrenApi.as_view(), name='node-add-children'),
    url(r'^v1/nodes/(?P<pk>[0-9a-zA-Z\-]{36})/assets/add/$', api.NodeAddAssetsApi.as_view(), name='node-add-assets'),
    url(r'^v1/nodes/(?P<pk>[0-9a-zA-Z\-]{36})/assets/remove/$', api.NodeRemoveAssetsApi.as_view(), name='node-remove-assets'),
]

urlpatterns += router.urls

