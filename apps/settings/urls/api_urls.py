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
    path('wecom/testing/', api.WeComTestingAPI.as_view(), name='wecom-testing'),
    path('dingtalk/testing/', api.DingTalkTestingAPI.as_view(), name='dingtalk-testing'),
    path('feishu/testing/', api.FeiShuTestingAPI.as_view(), name='feishu-testing'),
    path('alibaba/testing/', api.AlibabaSMSTestingAPI.as_view(), name='alibaba-sms-testing'),
    path('tencent/testing/', api.TencentSMSTestingAPI.as_view(), name='tencent-sms-testing'),
    path('sms/backend/', api.SMSBackendAPI.as_view(), name='sms-backend'),

    path('setting/', api.SettingsApi.as_view(), name='settings-setting'),
    path('public/', api.PublicSettingApi.as_view(), name='public-setting'),
]
