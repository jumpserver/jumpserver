from __future__ import absolute_import

from django.urls import path

from .. import api

app_name = 'common'

urlpatterns = [
    path('mail/testing/', api.MailTestingAPI.as_view(), name='mail-testing'),
    path('ldap/testing/', api.LDAPTestingAPI.as_view(), name='ldap-testing'),
    # path('django-settings/', api.DjangoSettingsAPI.as_view(), name='django-settings'),
]
