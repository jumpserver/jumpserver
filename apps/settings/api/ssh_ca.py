from types import SimpleNamespace

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.services import get_ssh_ca_client
from .. import serializers

__all__ = ['SSHCAOpenBaoTestingAPI', 'SSHCAOpenBaoPublicKeyAPI']


class SSHCAOpenBaoTestingAPI(GenericAPIView):
    serializer_class = serializers.SSHCAOpenBaoSerializer
    rbac_perms = {'POST': 'settings.change_vault'}

    def get_config(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = {}
        for name in serializer.fields:
            value = serializer.validated_data.get(name)
            if value in ('', None):
                value = getattr(settings, name, None)
            data[name] = value
        return SimpleNamespace(**data)

    def post(self, request):
        client = get_ssh_ca_client(self.get_config(request))
        ok, error = client.is_active()
        if not ok:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'msg': error},
            )
        return Response({
            'msg': _('Test success'),
            'public_key': client.get_public_key(),
        })


class SSHCAOpenBaoPublicKeyAPI(APIView):
    rbac_perms = {'GET': 'settings.change_vault'}

    def get(self, request):
        try:
            public_key = get_ssh_ca_client().get_public_key()
        except Exception as e:
            return Response(
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
                data={'msg': str(e)},
            )
        return Response({'public_key': public_key})
