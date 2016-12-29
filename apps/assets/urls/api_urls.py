# coding:utf-8
from django.conf.urls import url
from .. import api
from rest_framework import routers

app_name = 'assets'


router = routers.DefaultRouter()
router.register(r'v1/asset-groups', api.AssetGroupViewSet, 'asset-group')
router.register(r'v1/assets', api.AssetViewSet, 'asset')
router.register(r'v1/idc', api.IDCViewSet, 'idc')
router.register(r'v1/admin-user', api.AdminUserViewSet, 'admin-user')
router.register(r'v1/system-user', api.SystemUserViewSet, 'system-user')

urlpatterns = [
    url(r'^v1/assets_bulk/$', api.AssetListUpdateApi.as_view(), name='asset-bulk-update'),
    # url(r'^v1/idc/(?P<pk>[0-9]+)/assets/$', api.IDCAssetsApi.as_view(), name='api-idc-assets'),
    url(r'^v1/system-user/(?P<pk>[0-9]+)/auth-info/', api.SystemUserAuthInfoApi.as_view(),
        name='system-user-auth-info'),
    url(r'^v1/assets/(?P<pk>\d+)/groups/$',
        api.AssetUpdateGroupApi.as_view(), name='asset-update-group'),
    url(r'^v1/assets/(?P<pk>\d+)/system-users/$',
        api.SystemUserUpdateApi.as_view(), name='asset-update-system-users'),
]

urlpatterns += router.urls

