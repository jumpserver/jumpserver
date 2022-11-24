# coding:utf-8

from .asset_permission import asset_permission_urlpatterns
from .user_permission import user_permission_urlpatterns

app_name = 'perms'

urlpatterns = asset_permission_urlpatterns + user_permission_urlpatterns
