# coding:utf-8

from .asset_permission import asset_permission_urlpatterns

app_name = 'perms'

urlpatterns = []
urlpatterns += asset_permission_urlpatterns
