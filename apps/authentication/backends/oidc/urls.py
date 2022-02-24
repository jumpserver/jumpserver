"""
    OpenID Connect relying party (RP) URLs
    ======================================

    This modules defines the URLs allowing to perform OpenID Connect flows on a Relying Party (RP).
    It defines three main endpoints: the authentication request endpoint, the authentication
    callback endpoint and the end session endpoint.

"""

from django.urls import path

from . import views


urlpatterns = [
    path('login/', views.OIDCAuthRequestView.as_view(), name='login'),
    path('callback/', views.OIDCAuthCallbackView.as_view(), name='login-callback'),
    path('logout/', views.OIDCEndSessionView.as_view(), name='logout'),
]
