# -*- coding: utf-8 -*-
# 

from django.conf.urls import url, include
import api

app_name = 'users'

urlpatterns = [
    url(r'^v1/users/$', api.UserListAddApi.as_view(), name='user-list-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)/$', api.UserDetailDeleteUpdateApi.as_view(), name='user-detail-api'),
    url(r'^v1/usergroups/$', api.UserGroupListAddApi.as_view(), name='usergroup-list-api'),
    url(r'^v1/usergroups/(?P<pk>[0-9]+)/$', api.UserGroupDetailDeleteUpdateApi.as_view(), name='usergroup-detail-api'),
]
