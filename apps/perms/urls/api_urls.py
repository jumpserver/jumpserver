# coding:utf-8

from django.urls import re_path
from common import api as capi
from .asset_permission import asset_permission_urlpatterns
from .application_permission import remote_app_permission_urlpatterns

app_name = 'perms'


old_version_urlpatterns = [
    re_path('(?P<resource>user|user-group|asset-permission|remote-app-permission)/.*', capi.redirect_plural_name_api)
]

urlpatterns = asset_permission_urlpatterns + \
              remote_app_permission_urlpatterns \
              + old_version_urlpatterns

