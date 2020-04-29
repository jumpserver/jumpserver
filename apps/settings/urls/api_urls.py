from __future__ import absolute_import

from django.urls import path

from .. import api

app_name = 'common'

urlpatterns = [
    path('mail/testing/', api.MailTestingAPI.as_view(), name='mail-testing'),
    path('ldap/testing/config/', api.LDAPTestingConfigAPI.as_view(), name='ldap-testing-config'),
    path('ldap/testing/login/', api.LDAPTestingLoginAPI.as_view(), name='ldap-testing-login'),
    path('ldap/users/', api.LDAPUserListApi.as_view(), name='ldap-user-list'),
    path('ldap/users/import/', api.LDAPUserImportAPI.as_view(), name='ldap-user-import'),
    path('ldap/cache/refresh/', api.LDAPCacheRefreshAPI.as_view(), name='ldap-cache-refresh'),

    path('basic/', api.BasicSettingApi.as_view(), name='basic-settings'),
    path('email/', api.EmailSettingApi.as_view(), name='email-settings'),
    path('email-content/', api.EmailContentSettingApi.as_view(), name='email-content-settings'),
    path('ldap/', api.LdapSettingApi.as_view(), name='ldap-settings'),
    path('terminal/', api.TerminalSettingApi.as_view(), name='terminal-settings'),
    path('security/', api.SecuritySettingApi.as_view(), name='security-settings'),
    path('public/', api.PublicSettingApi.as_view(), name='public-setting'),
]
