# coding:utf-8
from django.conf.urls import url, include
import views
import api
from rest_framework import routers

app_name = 'assets'

urlpatterns = [
    # Resource asset url
    url(r'^$', views.AssetListView.as_view(), name='asset-index'),
    url(r'^asset$', views.AssetListView.as_view(), name='asset-list'),
    url(r'^asset/create$', views.AssetCreateView.as_view(), name='asset-create'),
    url(r'^asset/(?P<pk>[0-9]+)$', views.AssetDetailView.as_view(), name='asset-detail'),
    url(r'^asset/(?P<pk>[0-9]+)/update', views.AssetUpdateView.as_view(), name='asset-update'),
    url(r'^asset/(?P<pk>[0-9]+)/delete$', views.AssetDeleteView.as_view(), name='asset-delete'),
    url(r'^asset-modal$', views.AssetModalListView.as_view(), name='asset-modal-list'),
    url(r'^asset-modal-update$', views.AssetModalCreateView.as_view(), name='asset-modal-update'),

    # Resource asset group url
    url(r'^asset-group$', views.AssetGroupListView.as_view(), name='asset-group-list'),
    url(r'^asset-group/create$', views.AssetGroupCreateView.as_view(), name='asset-group-create'),
    url(r'^asset-group/(?P<pk>[0-9]+)$', views.AssetGroupDetailView.as_view(), name='asset-group-detail'),
    url(r'^asset-group/(?P<pk>[0-9]+)/update$', views.AssetGroupUpdateView.as_view(), name='asset-group-update'),
    url(r'^asset-group/(?P<pk>[0-9]+)/delete$', views.AssetGroupDeleteView.as_view(), name='asset-group-delete'),

    url(r'^tags$', views.TagsListView.as_view(), name='asset-tag-list'),
    url(r'^asset-by-tag/(?P<tag_id>[0-9]+)$', views.TagView.as_view(), name='asset-tags'),
    url(r'^tags/create$', views.AssetTagCreateView.as_view(), name='asset-tag-create'),
    url(r'^asset-tag/(?P<pk>[0-9]+)$', views.AssetTagDetailView.as_view(), name='asset-tag-detail'),
    url(r'^asset-tag/(?P<pk>[0-9]+)/update$', views.AssetTagUpdateView.as_view(), name='asset-tag-update'),
    url(r'^asset-tag/(?P<pk>[0-9]+)/delete$', views.AssetTagDeleteView.as_view(), name='asset-tag-delete'),

    # Resource idc url
    url(r'^idc$', views.IDCListView.as_view(), name='idc-list'),
    url(r'^idc/create$', views.IDCCreateView.as_view(), name='idc-create'),
    url(r'^idc/(?P<pk>[0-9]+)$', views.IDCDetailView.as_view(), name='idc-detail'),
    url(r'^idc/(?P<pk>[0-9]+)/update', views.IDCUpdateView.as_view(), name='idc-update'),
    url(r'^idc/(?P<pk>[0-9]+)/delete$', views.IDCDeleteView.as_view(), name='idc-delete'),
    url(r'^idc/(?P<pk>[0-9]+)/assets$', views.IDCAssetsView.as_view(), name='idc-assets'),

    # Resource admin user url
    url(r'^admin-user$', views.AdminUserListView.as_view(), name='admin-user-list'),
    url(r'^admin-user/create$', views.AdminUserCreateView.as_view(), name='admin-user-create'),
    url(r'^admin-user/(?P<pk>[0-9]+)$', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    url(r'^admin-user/(?P<pk>[0-9]+)/update', views.AdminUserUpdateView.as_view(), name='admin-user-update'),
    url(r'^admin-user/(?P<pk>[0-9]+)/delete$', views.AdminUserDeleteView.as_view(), name='admin-user-delete'),

    # Resource system user url
    url(r'^system-user$', views.SystemUserListView.as_view(), name='system-user-list'),
    url(r'^system-user/create$', views.SystemUserCreateView.as_view(), name='system-user-create'),
    url(r'^system-user/(?P<pk>[0-9]+)$', views.SystemUserDetailView.as_view(), name='system-user-detail'),
    url(r'^system-user/(?P<pk>[0-9]+)/update', views.SystemUserUpdateView.as_view(), name='system-user-update'),
    url(r'^system-user/(?P<pk>[0-9]+)/delete$', views.SystemUserDeleteView.as_view(), name='system-user-delete'),
    url(r'^system-user/(?P<pk>[0-9]+)/asset$', views.SystemUserAssetView.as_view(), name='system-user-asset'),
    # url(r'^system-user/(?P<pk>[0-9]+)/asset-group$', views.SystemUserAssetGroupView.as_view(),
    #     name='system-user-asset-group'),

]

router = routers.DefaultRouter()
router.register(r'v1/asset-groups', api.AssetGroupViewSet, 'api-asset-group')
router.register(r'v1/assets', api.AssetViewSet, 'api-asset')
router.register(r'v1/idc', api.IDCViewSet, 'api-idc')
router.register(r'v1/admin-user', api.AdminUserViewSet, 'api-admin-user')
router.register(r'v1/system-user', api.SystemUserViewSet, 'api-system-user')

urlpatterns += [
    url(r'^v1/assets_bulk/$', api.AssetListUpdateApi.as_view(), name='api-asset-bulk-update'),
    # url(r'^v1/idc/(?P<pk>[0-9]+)/assets/$', api.IDCAssetsApi.as_view(), name='api-idc-assets'),
    url(r'^v1/system-user/auth/', api.SystemUserAuthApi.as_view(), name='api-system-user-auth'),
]

urlpatterns += router.urls
