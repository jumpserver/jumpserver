# coding:utf-8
from django.conf.urls import patterns, include, url
from jlog.views import *

urlpatterns = patterns('',
                       url(r'^$', log_list),
                       url(r'^log_list/(\w+)/$', log_list),
                       url(r'^history/$', log_history),
                       url(r'^log_kill/', log_kill),
                       url(r'^record/$', log_record),
                      )