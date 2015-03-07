# coding:utf-8
from django.conf.urls import patterns, include, url
from jasset.views import *

urlpatterns = patterns('',
    url(r'^$', index),
    url(r'^host_add/$', add_host),
    url(r"^host_add_multi/$", add_host_multi),
    url(r'^host_list/$', list_host),
    url(r'^search/$', host_search),
    url(r"^(\d+.\d+.\d+.\d+)/$", jlist_ip),
    url(r'^idc_add/$', add_idc),
    url(r'^idc_list/$', list_idc),
    url(r'^idc_detail/$', detail_idc),
    url(r'^idc_del/(\w+)/$', del_idc),
    url(r'^jgroup_add/$', add_group),
    url(r'^group_edit/$', edit_group),
    url(r'^jgroup_list/$', list_group),
    url(r'^group_detail/$', detail_group),
    url(r'^group_del_host/(\w+)/$', group_del_host),
    url(r'^group_del/(\w+)/$', group_del),
    url(r'^host_del/(\w+)/$', host_del),
    url(r'^host_edit/$', host_edit),
    url(r'^host_edit/batch/$', batch_host_edit),
    url(r'^test/$', test),
)