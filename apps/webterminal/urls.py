# coding:utf-8
from django.conf.urls import url
from .views import *
from django.contrib import admin
admin.autodiscover()

app_name = 'webterminal'

urlpatterns = [
    url(r'^$', TerminalView.as_view(), name='webterminal'),
]