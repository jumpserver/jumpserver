# coding:utf-8
from django.conf.urls import patterns, include, url
from jlog.views import *

urlpatterns = patterns('',
    url(r'^$', log_list_online),
    url(r'^log_list/online/$', log_list_online),
    url(r'^log_list/offline/$', log_list_offline),
    url(r'^log_kill/(\d+)', log_kill),
    url(r'^history/$', log_history),
    url(r'^search/$', log_search),
)