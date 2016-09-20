# coding:utf-8
from django.conf.urls import url

import views

app_name = 'terminal'

urlpatterns = [
    url(r'^web-terminal$', views.TerminalView.as_view(), name='web-terminal'),
]
