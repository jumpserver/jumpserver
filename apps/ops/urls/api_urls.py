# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from ops import api as v1_api

__all__ = ["urlpatterns"]

api_router = DefaultRouter()
api_router.register(r'host_alia', v1_api.HostAliaViewSet)
api_router.register(r'user_alia', v1_api.UserAliaViewSet)
api_router.register(r'cmd_alia', v1_api.CmdAliaViewSet)
api_router.register(r'runas_alia', v1_api.RunasAliaViewSet)
api_router.register(r'extra_conf', v1_api.ExtraconfViewSet)
api_router.register(r'privilege', v1_api.PrivilegeViewSet)
api_router.register(r'sudo', v1_api.SudoViewSet)
api_router.register(r'cron', v1_api.CronTableViewSet)

urlpatterns = api_router.urls