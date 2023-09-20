from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.views import Response

from users.utils import LoginIpBlockUtil
from ..serializers import SecurityBlockIPSerializer


class BlockIPSecurityAPI(ListAPIView):
    serializer_class = SecurityBlockIPSerializer
    rbac_perms = {
        'GET': 'settings.change_security',
        'unlock': 'settings.change_security',
    }

    @staticmethod
    def get_ips():
        ips = []
        prefix = LoginIpBlockUtil.BLOCK_KEY_TMPL.replace('{}', '')
        keys = cache.keys(f'{prefix}*')
        for key in keys:
            ips.append(key.replace(prefix, ''))

        white_list = settings.SECURITY_LOGIN_IP_WHITE_LIST
        ips = list(set(ips) - set(white_list))
        ips = [ip for ip in ips if ip != '*']
        return ips

    def get_page_offset_and_limit(self):
        get_params = self.request.GET
        offset = get_params.get('offset', 0)
        limit = get_params.get('limit', 15)
        return int(offset), int(limit)

    def list(self, request, *args, **kwargs):
        ips = self.get_ips()
        offset, limit = self.get_page_offset_and_limit()
        slice_ips = ips[offset:offset + limit]
        data = [{'id': str(uuid4()), 'ip': ip} for ip in slice_ips]
        ser = self.get_serializer(data, many=True)
        data = {'count': len(ips), 'results': ser.data}
        return Response(data=data, status=200)


class UnlockIPSecurityAPI(CreateAPIView):
    serializer_class = SecurityBlockIPSerializer
    rbac_perms = {
        'POST': 'settings.change_security',
    }

    def create(self, request, *args, **kwargs):
        ips = request.data.get('ips')
        for ip in ips:
            LoginIpBlockUtil(ip).clean_block_if_need()
        return Response(status=200)
