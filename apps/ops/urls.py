# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from django.conf.urls import url, include


from api import views as api_view
import views as page_view


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
    url(r'^sudo/list$',   page_view.SudoListView.as_view(),   name='page-sudo-list'),
    url(r'^sudo/create$', page_view.SudoCreateView.as_view(), name='page-sudo-create'),
    url(r'^sudo/detail$', page_view.SudoDetailView.as_view(), name='page-sudo-detail'),
    url(r'^sudo/update$', page_view.SudoUpdateView.as_view(), name='page-sudo-update'),

    # Resource Cron url
    url(r'^cron/list$',   page_view.CronListView.as_view(),   name='page-cron-list'),
    url(r'^cron/create$', page_view.CronCreateView.as_view(), name='page-cron-create'),
    url(r'^cron/detail$', page_view.CronDetailView.as_view(), name='page-cron-detail'),
    url(r'^cron/update$', page_view.CronUpdateView.as_view(), name='page-cron-update'),
]

urlpatterns += [
    url(r'^v1/sudo', include(router.urls)),
]


