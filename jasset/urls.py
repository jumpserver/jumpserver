# coding:utf-8
from django.conf.urls import patterns, include, url
from jasset.views import *

urlpatterns = patterns('',
    url(r'^$', index),
    url(r'jadd', jadd),
    url(r'jlist', jlist),
    url(r'jadd_idc', jadd_idc),
    url(r'jlist_idc', jlist_idc),
)