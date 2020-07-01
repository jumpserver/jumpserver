from django.urls import path
from access_control import views

app_name = 'access_control'

urlpatterns = [
    path('access-control/', views.AccessControlListView.as_view(), name='access-control-list'),
    path('access-control/create/', views.AccessControlCreateView.as_view(), name='access-control-create'),
]
