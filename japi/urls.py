# coding:utf-8
from django.conf.urls import patterns, url
from japi.views import *

urlpatterns = patterns('',
    # jasset
    # TODO: 其他接口待实现
    # url(r'^asset/list/$', asset_list, name='api_asset_list'),
    # url(r"^asset/detail/$", asset_detail, name='api_asset_detail'),
    url(r'^group/list/$', group_list, name='api_asset_group_list'),
    # url(r'^idc/list/$', idc_list, name='api_idc_list'),

    # jperm
    url(r'^role/list/$', perm_role_list, name='api_role_list'),
)