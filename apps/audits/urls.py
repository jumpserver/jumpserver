from django.conf.urls import url


import api
import views

app_name = 'audits'

urlpatterns = [
    url(r'^proxy-log$', views.ProxyLogListView.as_view(), name='proxy-log-list'),
    url(r'^proxy-log/(?P<pk>\d+)$', views.ProxyLogDetailView.as_view(), name='proxy-log-detail'),
]


urlpatterns += [
    url(r'^v1/proxy-log/$', api.ProxyLogListCreateApi.as_view(), name='proxy-log-list-create-api'),
    url(r'^v1/proxy-log/(?P<pk>\d+)/$', api.ProxyLogDetailApi.as_view(), name='proxy-log-detail-api'),
    url(r'^v1/command-log/$', api.CommandLogCreateApi.as_view(), name='command-log-create-list-api'),
]
