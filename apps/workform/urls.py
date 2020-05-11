'''
work_form的urls
'''

from django.urls import path, re_path
from . import views

app_name = 'workform'

urlpatterns = [
    path('service_msg/', views.service_msg, name='service_msg'),
]