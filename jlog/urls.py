# coding:utf-8
from django.conf.urls import patterns, include, url
from jlog.views import *

urlpatterns = patterns('',
    url(r'^$', jlog_list),
    url(r'^log_list/$', jlog_list),
    url(r'^log_kill/(\d+)', jlog_kill),
)
