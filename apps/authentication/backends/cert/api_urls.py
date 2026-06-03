
from django.urls import path
from . import api

urlpatterns = [
    # api
    path('cert/vendor-driver.js/', api.VendorDriverFileAPIView.as_view(), name='cert-vendor-driver-js-file'),
    path('cert/vendor-driver-config/', api.CertVendorDriverConfigAPIView.as_view(), name='cert-vendor-driver-config'),
    path('cert/enroll/', api.CertEnrollAPIView.as_view(), name='cert-enroll'),
    path('ukey/bind-user-sn/', api.BindUserUkeySnAPIView.as_view(), name='bind-user-ukey-sn'),
]
