from django.conf.urls import url
from .. import views

app_name = 'audits'

urlpatterns = [
    url(r'^proxy-log-offline/$', views.ProxyLogOfflineListView.as_view(),
        name='proxy-log-offline-list'),
    url(r'^proxy-log-online/$', views.ProxyLogOnlineListView.as_view(),
        name='proxy-log-online-list'),
    url(r'^proxy-log/(?P<pk>\d+)/$', views.ProxyLogDetailView.as_view(),
        name='proxy-log-detail'),
    # url(r'^proxy-log/(?P<pk>\d+)/commands$', views.ProxyLogCommandsListView.as_view(), name='proxy-log-commands-list'),
    url(r'^command-log/$', views.CommandLogListView.as_view(),
        name='command-log-list'),
    url(r'^login-log/$', views.LoginLogListView.as_view(),
        name='login-log-list'),
]


