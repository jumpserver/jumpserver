from rest_framework.views import Response
from rest_framework.generics import GenericAPIView
from rest_framework import status
from django.utils.translation import gettext_lazy as _

from ..backends import VaultClient, vault_client
from common.permissions import IsSuperUser

from .. import serializers

__all__ = ['VaultConnectTestingAPI', ]


class VaultConnectTestingAPI(GenericAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.VaultConnectTestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data['VAULT_URL']
        token = serializer.validated_data.get('VAULT_TOKEN')

        client = VaultClient(url)
        client.check_base_token_authentication(token)
        if client.is_active:
            setattr(vault_client, 'client', client.client)
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': _('Test fail')})
