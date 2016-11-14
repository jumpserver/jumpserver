from django.conf.urls import url

from rest_framework import routers

import api
import views

app_name = 'audits'

urlpatterns = [
    url(r'^proxy-log$', views.ProxyLogListView.as_view(), name='proxy-log-list'),
    url(r'^proxy-log/(?P<pk>\d+)$', views.ProxyLogDetailView.as_view(), name='proxy-log-detail'),
    url(r'^proxy-log/(?P<pk>\d+)/commands$', views.ProxyLogCommandsListView.as_view(), name='proxy-log-commands-list'),
    url(r'^command-log$', views.CommandLogListView.as_view(), name='command-log-list'),
    url(r'^login-log$', views.LoginLogListView.as_view(), name='login-log-list'),
]

router = routers.DefaultRouter()
router.register(r'v1/proxy-log', api.ProxyLogViewSet, 'api-proxy-log')
router.register(r'v1/command-log', api.CommandLogViewSet, 'api-command-log')

urlpatterns += router.urls
