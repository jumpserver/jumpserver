# coding:utf-8
from django.conf.urls import patterns, include, url
from jasset.views import *

urlpatterns = patterns('',
    url(r'^asset/add/$', asset_add, name='asset_add'),
    url(r"^asset/add_batch/$", asset_add_batch, name='asset_add_batch'),
    url(r'^asset/list/$', asset_list, name='asset_list'),
    url(r'^asset/del/$', asset_del, name='asset_del'),
    url(r"^asset/detail/$", asset_detail, name='asset_detail'),
    url(r'^asset/edit/$', asset_edit, name='asset_edit'),
    url(r'^asset/edit_batch/$', asset_edit_batch, name='asset_edit_batch'),
    url(r'^asset/update/$', asset_update, name='asset_update'),
    url(r'^asset/update_batch/$', asset_update_batch, name='asset_update_batch'),
    url(r'^asset/upload/$', asset_upload, name='asset_upload'),
    url(r'^group/del/$', group_del, name='asset_group_del'),
    url(r'^group/add/$', group_add, name='asset_group_add'),
    url(r'^group/list/$', group_list, name='asset_group_list'),
    url(r'^group/edit/$', group_edit, name='asset_group_edit'),
    url(r'^idc/add/$', idc_add, name='idc_add'),
    url(r'^idc/list/$', idc_list, name='idc_list'),
    url(r'^idc/edit/$', idc_edit, name='idc_edit'),
    url(r'^idc/del/$', idc_del, name='idc_del'),
)