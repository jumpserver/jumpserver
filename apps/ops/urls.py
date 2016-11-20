# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from rest_framework.routers import DefaultRouter
from django.conf.urls import url, include


from api import views as api_view
import views as mvc_view


app_name = 'ops'

router = DefaultRouter()
router.register(r'HostAlias',  api_view.HostAliaViewSet)
router.register(r'UserAlias',  api_view.UserAliaViewSet)
router.register(r'CmdAlias',   api_view.CmdAliaViewSet)
router.register(r'RunasAlias', api_view.RunasAliaViewSet)
router.register(r'Extraconf',  api_view.ExtraconfViewSet)

urlpatterns = [
    # Resource Sudo url
    url(r'^sudo/list$',  mvc_view.SudoListView.as_view(), name='sudo-list'),
    url(r'^sudo/create', mvc_view.SudoCreateView(), name='sudo-create'),
    url(r'^sudo/detail', mvc_view.SudoDetailView(), name='sudo-detail'),
    url(r'^sudo/update', mvc_view.SudoUpdateView(), name='sudo-update'),
    url(r'^sudo/delete', mvc_view.SudoDeleteView(), name='sudo-delete'),
]

urlpatterns += [
    url(r'^api/ops/sudo', include(router.urls)),
]


