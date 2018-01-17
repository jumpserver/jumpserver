from __future__ import absolute_import

from django.conf.urls import url

from .. import views

app_name = 'common'

urlpatterns = [
    url(r'^$', views.BasicSettingView.as_view(), name='basic-setting'),
    url(r'^email/$', views.EmailSettingView.as_view(), name='email-setting'),
    url(r'^ldap/$', views.LDAPSettingView.as_view(), name='ldap-setting'),
    url(r'^storage/$', views.StorageSettingView.as_view(), name='storage-setting'),
]
