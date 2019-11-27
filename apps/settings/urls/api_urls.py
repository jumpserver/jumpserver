from __future__ import absolute_import

from django.urls import path

from .. import api

app_name = 'common'

urlpatterns = [
    path('mail/testing/', api.MailTestingAPI.as_view(), name='mail-testing'),
    path('ldap/testing/', api.LDAPTestingAPI.as_view(), name='ldap-testing'),
    path('ldap/users/', api.LDAPUserListApi.as_view(), name='ldap-user-list'),
    path('ldap/users/import/', api.LDAPUserImportAPI.as_view(), name='ldap-user-import'),
    path('ldap/cache/refresh/', api.LDAPCacheRefreshAPI.as_view(), name='ldap-cache-refresh'),

    path('public/', api.PublicSettingApi.as_view(), name='public-setting'),
]
