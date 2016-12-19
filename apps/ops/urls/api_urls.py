# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from ops import api as v1_api

__all__ = ["urlpatterns"]

api_router = DefaultRouter()
api_router.register(r'v1/host_alia', v1_api.HostAliaViewSet)
api_router.register(r'v1/user_alia', v1_api.UserAliaViewSet)
api_router.register(r'v1/cmd_alia', v1_api.CmdAliaViewSet)
api_router.register(r'v1/runas_alia', v1_api.RunasAliaViewSet)
api_router.register(r'v1/extra_conf', v1_api.ExtraconfViewSet)
api_router.register(r'v1/privilege', v1_api.PrivilegeViewSet)
api_router.register(r'v1/sudo', v1_api.SudoViewSet)
api_router.register(r'v1/cron', v1_api.CronTableViewSet)
api_router.register(r'v1/task', v1_api.TaskViewSet)

urlpatterns = api_router.urls