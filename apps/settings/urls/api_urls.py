from __future__ import absolute_import

from django.urls import path

from .. import api

app_name = 'common'

urlpatterns = [
    path('mail/testing/', api.MailTestingAPI.as_view(), name='mail-testing'),
    path('ldap/testing/', api.LDAPTestingAPI.as_view(), name='ldap-testing'),
    path('ldap/users/', api.LDAPUserListApi.as_view(), name='ldap-user-list'),
    path('ldap/users/sync/', api.LDAPUserSyncAPI.as_view(), name='ldap-user-sync'),
    path('terminal/replay-storage/create/', api.ReplayStorageCreateAPI.as_view(), name='replay-storage-create'),
    path('terminal/replay-storage/delete/', api.ReplayStorageDeleteAPI.as_view(), name='replay-storage-delete'),
    path('terminal/command-storage/create/', api.CommandStorageCreateAPI.as_view(), name='command-storage-create'),
    path('terminal/command-storage/delete/', api.CommandStorageDeleteAPI.as_view(), name='command-storage-delete'),
    path('django-settings/', api.DjangoSettingsAPI.as_view(), name='django-settings'),
]
