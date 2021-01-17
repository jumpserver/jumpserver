# coding:utf-8

from django.urls import re_path
from common import api as capi
from .asset_permission import asset_permission_urlpatterns
from .application_permission import application_permission_urlpatterns
from .system_user_permission import system_users_permission_urlpatterns

app_name = 'perms'

old_version_urlpatterns = [
    re_path('(?P<resource>user|user-group|asset-permission|remote-app-permission)/.*', capi.redirect_plural_name_api)
]

urlpatterns = []
urlpatterns += asset_permission_urlpatterns
urlpatterns += application_permission_urlpatterns
urlpatterns += system_users_permission_urlpatterns
urlpatterns += old_version_urlpatterns
