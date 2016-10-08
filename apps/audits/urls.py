from django.conf.urls import url


import api
import views

app_name = 'audits'

urlpatterns = [
]


urlpatterns += [
    url(r'^v1/proxy-log$', api.ProxyLogCreateApi.as_view(), name='proxy-log-create-api'),
    url(r'^v1/command-log$', api.CommandLogCreateApi.as_view(), name='command-log-create-api'),
]
