from django.conf.urls import url
from . import views

app_name = 'users'

urlpatterns = [
    url(r'hello/$', views.hello, name='hello'),
]
