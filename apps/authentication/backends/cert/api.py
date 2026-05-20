
import os

import yaml
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from common.permissions import OnlySuperUser


__all__ = ['VendorDriverFileAPIView', 'CertVendorDriverConfigAPIView']


class VendorDriverFileAPIView(APIView):
    permission_classes = (OnlySuperUser,)

    def get(self, request):
        js_file = getattr(settings, 'AUTH_CERT_VENDOR_DRIVER_FILE', None)
        if not js_file or not os.path.isfile(js_file):
            raise Http404
        return FileResponse(open(js_file, 'rb'), content_type='application/javascript')


class CertVendorDriverConfigAPIView(APIView):
    # TODO: auth-cert
    permission_classes = (OnlySuperUser,)

    def get(self, request):
        config_file = getattr(settings, 'AUTH_CERT_VENDOR_DRIVER_CONFIG_FILE', None)
        if not config_file or not os.path.isfile(config_file):
            raise Http404
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return Response(data)
