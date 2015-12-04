# coding:utf-8
from django.conf.urls import patterns, include, url
from jlog.views import *

urlpatterns = patterns('',
                       (r'^$', log_list),
                       (r'^log_list/(\w+)/$', log_list),
                       (r'^log_detail/(\w+)/$', log_detail),
                       (r'^history/$', log_history),
                       (r'^log_kill/', log_kill),
                       (r'^record/$', log_record),
                       (r'^web_terminal/$', web_terminal),
                      )