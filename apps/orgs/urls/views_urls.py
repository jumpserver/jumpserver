# -*- coding: utf-8 -*-
#

from django.conf.urls import url
from .. import views

app_name = 'orgs'


urlpatterns = [
    url(r'^(?P<pk>.*)/switch/$', views.SwitchOrgView.as_view(), name='org-switch')
]

