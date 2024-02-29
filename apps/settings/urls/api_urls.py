from __future__ import absolute_import

from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from .. import api

app_name = 'common'
router = BulkRouter()
router.register(r'chatai-prompts', api.ChatPromptViewSet, 'chatai-prompt')

urlpatterns = [
    path('mail/testing/', api.MailTestingAPI.as_view(), name='mail-testing'),
    path('ldap/users/', api.LDAPUserListApi.as_view(), name='ldap-user-list'),
    path('wecom/testing/', api.WeComTestingAPI.as_view(), name='wecom-testing'),
    path('dingtalk/testing/', api.DingTalkTestingAPI.as_view(), name='dingtalk-testing'),
    path('feishu/testing/', api.FeiShuTestingAPI.as_view(), name='feishu-testing'),
    path('slack/testing/', api.SlackTestingAPI.as_view(), name='slack-testing'),
    path('sms/<str:backend>/testing/', api.SMSTestingAPI.as_view(), name='sms-testing'),
    path('sms/backend/', api.SMSBackendAPI.as_view(), name='sms-backend'),
    path('vault/testing/', api.VaultTestingAPI.as_view(), name='vault-testing'),
    path('chatai/testing/', api.ChatAITestingAPI.as_view(), name='chatai-testing'),
    path('vault/sync/', api.VaultSyncDataAPI.as_view(), name='vault-sync'),
    path('security/block-ip/', api.BlockIPSecurityAPI.as_view(), name='block-ip'),
    path('security/unlock-ip/', api.UnlockIPSecurityAPI.as_view(), name='unlock-ip'),

    path('setting/', api.SettingsApi.as_view(), name='settings-setting'),
    path('logo/', api.SettingsLogoApi.as_view(), name='settings-logo'),
    path('public/', api.PublicSettingApi.as_view(), name='public-setting'),
    path('public/open/', api.OpenPublicSettingApi.as_view(), name='open-public-setting'),
    path('server-info/', api.ServerInfoApi.as_view(), name='server-info'),
]

urlpatterns += router.urls
