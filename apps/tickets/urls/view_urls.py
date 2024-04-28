# coding:utf-8
#

from django.conf import settings
from django.urls import path

from .. import views

app_name = 'tickets'

urlpatterns = [
    path('direct-approve/<str:token>/', views.TicketDirectApproveView.as_view(), name='direct-approve'),
]

if not settings.TICKETS_ENABLED:
    urlpatterns = []
