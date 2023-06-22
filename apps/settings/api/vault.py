from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import Response, APIView

from accounts.backends import VAULT_CLIENT_MAPPER
from accounts.tasks.vault import sync_account_vault_data
from settings.models import Setting
from .. import serializers


class VaultTestingAPI(GenericAPIView):
    serializer_class = serializers.VaultSettingSerializer
    rbac_perms = {
        'POST': 'settings.change_vault'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        vault_type = serializer.validated_data['VAULT_TYPE']
        hcp_vault_host = serializer.validated_data['HCP_VAULT_HOST']
        hcp_vault_token = serializer.validated_data.get('HCP_VAULT_TOKEN')

        if not hcp_vault_token:
            token = Setting.objects.filter(name='HCP_VAULT_TOKEN').first()
            if token:
                hcp_vault_token = token.value

        vault_token = hcp_vault_token or ''
        vault_client = VAULT_CLIENT_MAPPER.get(vault_type)
        if vault_client.is_active(hcp_vault_host, vault_token):
            return Response(status=status.HTTP_200_OK, data={'msg': _('Test success')})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'Test failed'})


class VaultSyncDataAPI(APIView):
    perm_model = Setting
    rbac_perms = {
        'POST': 'settings.change_vault'
    }

    def post(self, request, *args, **kwargs):
        task = sync_account_vault_data.delay()
        return Response({'task': task.id}, status=status.HTTP_201_CREATED)
