# coding:utf-8
from django.conf.urls import url
from .. import api
from rest_framework import routers
from rest_framework_bulk.routes import BulkRouter

app_name = 'assets'


router = BulkRouter()
router.register(r'v1/asset-groups', api.AssetGroupViewSet, 'asset-group')
router.register(r'v1/assets', api.AssetViewSet, 'asset')
router.register(r'v1/idc', api.IDCViewSet, 'idc')
router.register(r'v1/admin-user', api.AdminUserViewSet, 'admin-user')
router.register(r'v1/system-user', api.SystemUserViewSet, 'system-user')
router.register(r'v1/tags', api.TagViewSet, 'asset-tag')

urlpatterns = [
    url(r'^v1/assets_bulk/$', api.AssetListUpdateApi.as_view(), name='asset-bulk-update'),
    # url(r'^v1/idc/(?P<pk>[0-9]+)/assets/$', api.IDCAssetsApi.as_view(), name='api-idc-assets'),
    url(r'^v1/system-user/auth/', api.SystemUserAuthApi.as_view(), name='system-user-auth'),

    url(r'^v1/assets/(?P<pk>\d+)/groups/$',
        api.AssetUpdateGroupApi.as_view(), name='asset-update-group'),

    url(r'^v1/assets/(?P<pk>\d+)/system-users/$',
        api.SystemUserUpdateApi.as_view(), name='asset-update-systemusers'),

	## update the system users, which add and delete the asset to the system user
	url(r'^v1/system_user/(?P<pk>\d+)/assets/$',
	    api.SystemUserUpdateAssetsApi.as_view(), name='systemuser-update-assets'),

    url(r'^v1/system_user/(?P<pk>\d+)/groups/$',
        api.SystemUserUpdateAssetGroupApi.as_view(), name='systemuser-update-assetgroups'),

	## update the asset group, which add or delete the asset to the group
    url(r'^v1/groups/(?P<pk>\d+)/assets/$',
        api.AssetGroupUpdateApi.as_view(), name='asset-groups-update'),
	## update the asset group, and add or delete the system_user to the group
    url(r'^v1/groups/(?P<pk>\d+)/system-users/$',
        api.AssetGroupUpdateSystemUserApi.as_view(), name='asset-groups-update-systemusers'),
    ## update the IDC, and add or delete the assets to the IDC
    url(r'^v1/idc/(?P<pk>\d+)/assets/$',
        api.IDCupdateAssetsApi.as_view(), name='idc-update-assets'),

    url(r'v1/tag/(?P<pk>\d+)/assets/$',
        api.TagUpdateAssetsApi.as_view(), name='tag-update-assets'),


]

urlpatterns += router.urls

