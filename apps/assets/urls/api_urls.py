# coding:utf-8
from django.conf.urls import url
from .. import api
from rest_framework_bulk.routes import BulkRouter

app_name = 'assets'


router = BulkRouter()
router.register(r'v1/groups', api.AssetGroupViewSet, 'asset-group')
router.register(r'v1/assets', api.AssetViewSet, 'asset')
router.register(r'v1/clusters', api.ClusterViewSet, 'cluster')
router.register(r'v1/admin-user', api.AdminUserViewSet, 'admin-user')
router.register(r'v1/system-user', api.SystemUserViewSet, 'system-user')

urlpatterns = [
    url(r'^v1/assets-bulk/$', api.AssetListUpdateApi.as_view(), name='asset-bulk-update'),
    url(r'^v1/system-user/(?P<pk>[0-9a-zA-Z\-]{36})/auth-info/', api.SystemUserAuthInfoApi.as_view(),
        name='system-user-auth-info'),
    url(r'^v1/assets/(?P<pk>[0-9a-zA-Z\-]{36})/groups/$',
        api.AssetUpdateGroupApi.as_view(), name='asset-update-group'),
    url(r'^v1/assets/(?P<pk>[0-9a-zA-Z\-]{36})/refresh/$',
        api.AssetRefreshHardwareView.as_view(), name='asset-refresh'),
    url(r'^v1/assets/(?P<pk>[0-9a-zA-Z\-]{36})/admin-user-test/$',
        api.AssetAdminUserTestView.as_view(), name='asset-admin-user-test'),
    # update the asset group, which add or delete the asset to the group
    url(r'^v1/groups/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$',
        api.GroupUpdateAssetsApi.as_view(), name='group-update-assets'),
    url(r'^v1/groups/(?P<pk>[0-9a-zA-Z\-]{36})/assets/add/$',
        api.GroupAddAssetsApi.as_view(), name='group-add-assets'),
    # update the Cluster, and add or delete the assets to the Cluster
    url(r'^v1/cluster/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$',
        api.ClusterUpdateAssetsApi.as_view(), name='cluster-update-assets'),
    url(r'^v1/cluster/(?P<pk>[0-9a-zA-Z\-]{36})/assets/$',
        api.ClusterAddAssetsApi.as_view(), name='cluster-add-assets'),
    url(r'^v1/admin-user/(?P<pk>[0-9a-zA-Z\-]{36})/clusters/$',
        api.AdminUserAddClustersApi.as_view(), name='admin-user-add-clusters'),
]

urlpatterns += router.urls

