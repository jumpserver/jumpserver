from . import views

from django.urls import path

urlpatterns = [
    path('cert/login/', views.CertLoginView.as_view(), name='cert-login')
]
