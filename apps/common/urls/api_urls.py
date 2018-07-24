from __future__ import absolute_import

from django.conf.urls import url

from .. import api

app_name = 'common'

urlpatterns = [
    url(r'^mail/testing/$', api.MailTestingAPI.as_view(), name='mail-testing'),
    url(r'^ldap/testing/$', api.LDAPTestingAPI.as_view(), name='ldap-testing'),
    # url(r'^django-settings/$', api.DjangoSettingsAPI.as_view(), name='django-settings'),
]
