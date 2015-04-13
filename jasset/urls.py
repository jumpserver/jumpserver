# coding:utf-8
from django.conf.urls import patterns, include, url
from jasset.views import *

urlpatterns = patterns('',
    url(r'^host_add/$', host_add),
    url(r"^host_add_multi/$", host_add_batch),
    url(r'^host_list/$', host_list),
    url(r'^search/$', host_search),
    url(r"^host_detail/$", host_detail),
    url(r"^dept_host_ajax/$", dept_host_ajax),
    url(r'^idc_add/$', idc_add),
    url(r'^idc_list/$', idc_list),
    url(r'^idc_edit/$', idc_edit),
    url(r'^idc_detail/$', idc_detail),
    url(r'^idc_del/$', idc_del),
    url(r'^group_add/$', group_add),
    url(r'^group_edit/$', group_edit),
    url(r'^group_list/$', group_list),
    url(r'^group_detail/$', group_detail),
    url(r'^group_del_host/(\w+)/$', group_del_host),
    url(r'^group_del/$', group_del),
    url(r'^host_del/(\w+)/$', host_del),
    url(r'^host_edit/$', view_splitter, {'su': host_edit, 'adm': host_edit_adm}),
    url(r'^host_edit/batch/$', host_edit_batch),
    url(r'^host_edit_common/batch/$', host_edit_common_batch),
)