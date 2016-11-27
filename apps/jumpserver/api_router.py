from rest_framework.routers import DefaultRouter
from ops.api import views as ops_api_view

api_router = DefaultRouter()
api_router.register(r'host_alia', ops_api_view.HostAliaViewSet)
api_router.register(r'user_alia', ops_api_view.UserAliaViewSet)
api_router.register(r'cmd_alia', ops_api_view.CmdAliaViewSet)
api_router.register(r'runas_alia', ops_api_view.RunasAliaViewSet)
api_router.register(r'extra_conf', ops_api_view.ExtraconfViewSet)
api_router.register(r'privilege', ops_api_view.PrivilegeViewSet)
api_router.register(r'sudo', ops_api_view.SudoViewSet)
api_router.register(r'cron', ops_api_view.CronTableViewSet)