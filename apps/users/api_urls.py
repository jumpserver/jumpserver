# -*- coding: utf-8 -*-
# 

from django.conf.urls import url, include

from .api import UserListApi, UserDetailApi


urlpatterns = [
    url(r'^v1/users/$', UserListApi.as_view()),
    url(r'^v1/users/(?P<pk>[0-9]+)/$', UserDetailApi.as_view()),
]
