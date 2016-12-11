# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals


from django.conf.urls import url
from ops import views as page_view

__all__ = ["urlpatterns"]

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