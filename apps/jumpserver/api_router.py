from rest_framework.routers import DefaultRouter
from ops.api import views as ops_api_view

router = DefaultRouter()
router.register(r'host_alia',  ops_api_view.HostAliaViewSet)
router.register(r'user_alia',  ops_api_view.UserAliaViewSet)
router.register(r'cmd_alia',   ops_api_view.CmdAliaViewSet)
router.register(r'runas_alia', ops_api_view.RunasAliaViewSet)
router.register(r'extra_conf', ops_api_view.ExtraconfViewSet)
router.register(r'privilege',  ops_api_view.PrivilegeViewSet)
router.register(r'sudo',       ops_api_view.SudoViewSet)
router.register(r'cron',       ops_api_view.CronTableViewSet)