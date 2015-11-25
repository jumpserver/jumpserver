# coding:utf-8
from django.conf.urls import patterns, include, url
from jasset.views import *

urlpatterns = patterns('',
    url(r'^asset_add/$', asset_add),
    url(r"^asset_add_batch/$", asset_add_batch),
    url(r'^group_del/$', group_del),
    url(r'^asset_list/$', asset_list),
    url(r'^asset_del/$', asset_del),
    url(r"^asset_detail/$", asset_detail),
    url(r'^asset_edit/$', asset_edit),
    url(r'^asset_update/$', asset_update),
    url(r'^asset_update_batch/$', asset_update_batch),
    # url(r'^search/$', host_search),
    # url(r"^show_all_ajax/$", show_all_ajax),
    url(r'^group_add/$', group_add),
    url(r'^group_list/$', group_list),
    url(r'^group_edit/$', group_edit),
    url(r'^group_list/$', group_list),
    # url(r'^group_del_host/$', group_del_host),
    url(r'^asset_edit_batch/$', asset_edit_batch),
    # url(r'^host_edit_common/batch/$', host_edit_common_batch),
    url(r'^idc_add/$', idc_add),
    url(r'^idc_list/$', idc_list),
    url(r'^idc_edit/$', idc_edit),
    url(r'^idc_del/$', idc_del),
    url(r'^upload/$', asset_upload),
)