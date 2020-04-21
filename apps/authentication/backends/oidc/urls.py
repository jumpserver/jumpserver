from django.urls import path
from oidc_rp import views as oidc_rp_views
from .views import OverwriteOIDCEndSessionView


urlpatterns = [
    path('login/', oidc_rp_views.OIDCAuthRequestView.as_view(), name='oidc-login'),
    path('callback/', oidc_rp_views.OIDCAuthCallbackView.as_view(), name='oidc-callback'),
    path('logout/', OverwriteOIDCEndSessionView.as_view(), name='oidc-logout'),
]
