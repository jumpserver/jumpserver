from django.urls import path
from .. import api

system_users_permission_urlpatterns = [
    path('system-users-permission/', api.SystemUserPermission.as_view(), name='system-users-permission'),
]
