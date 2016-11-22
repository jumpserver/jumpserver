# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from django.conf.urls import url, include


from api import views as api_view
import views as mvc_view


app_name = 'ops'

router = DefaultRouter()
router.register(r'host_alia',  api_view.HostAliaViewSet)
router.register(r'user_alia',  api_view.UserAliaViewSet)
router.register(r'cmd_alia',   api_view.CmdAliaViewSet)
router.register(r'runas_alia', api_view.RunasAliaViewSet)
router.register(r'extra_conf', api_view.ExtraconfViewSet)
router.register(r'privilege',  api_view.PrivilegeViewSet)
router.register(r'sudo',       api_view.SudoViewSet)
router.register(r'cron',       api_view.CronTableViewSet)

urlpatterns = [
    # Resource Sudo url
    url(r'^sudo/list$',   mvc_view.SudoListView.as_view(),   name='sudo-list'),
    url(r'^sudo/create$', mvc_view.SudoCreateView.as_view(), name='sudo-create'),
    url(r'^sudo/detail$', mvc_view.SudoDetailView.as_view(), name='sudo-detail'),
    url(r'^sudo/update$', mvc_view.SudoUpdateView.as_view(), name='sudo-update'),
]

urlpatterns += [
    url(r'^v1/sudo', include(router.urls)),
]


