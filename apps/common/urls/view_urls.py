from __future__ import absolute_import

from django.conf.urls import url

from .. import views

app_name = 'common'

urlpatterns = [
    url(r'^$', views.BasicSettingView.as_view(), name='basic-setting'),
    url(r'^email/$', views.EmailSettingView.as_view(), name='email-setting'),
    url(r'^ldap/$', views.LDAPSettingView.as_view(), name='ldap-setting'),
    url(r'^terminal/$', views.TerminalSettingView.as_view(), name='terminal-setting'),

    url(r'^celery/task/(?P<pk>[0-9a-zA-Z\-]{36})/log/$', views.CeleryTaskLogView.as_view(), name='celery-task-log'),
]
