from . import views

from django.urls import path

urlpatterns = [
    path('login/', views.UKeyLoginView.as_view(), name='ukey-login')
]
