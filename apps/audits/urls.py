from django.conf.urls import url


import api
import views

app_name = 'audits'

urlpatterns = [
]


urlpatterns += [
    url(r'^v1/proxy-log/$', api.ProxyLogListCreateApi.as_view(), name='proxy-log-list-create-api'),
    url(r'^v1/proxy-log/(?P<pk>\d+)/$', api.ProxyLogDetailApi.as_view(), name='proxy-log-detail-api'),
    url(r'^v1/command-log/$', api.CommandLogCreateApi.as_view(), name='command-log-create-api'),
]
