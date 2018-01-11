from __future__ import absolute_import

from django.conf.urls import url

from .. import views

app_name = 'common'

urlpatterns = [
    url(r'^email/$', views.EmailSettingView.as_view(), name='email-setting'),
]
