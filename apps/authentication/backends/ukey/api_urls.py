
from django.urls import path
from . import api

app_name = 'ukey'

urlpatterns = [
    path('ukey-sdk.js/', api.UKeySDKScriptFileAPIView.as_view(), name='ukey-sdk-script'),
    path('ukey-sdk-config/', api.UKeySDKConfigFileAPIView.as_view(), name='ukey-sdk-config'),
    path('enroll-cert/', api.UKeyCertEnrollAPIView.as_view(), name='ukey-enroll-cert'),
]
