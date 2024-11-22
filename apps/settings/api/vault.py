from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import Response, APIView

from accounts.backends import get_vault_client
from accounts.tasks.vault import sync_secret_to_vault
from common.exceptions import JMSException
from settings.models import Setting
from .. import serializers


class VaultTestingAPI(GenericAPIView):
    backends_serializer = {
        'azure': serializers.AzureKVSerializer,
        'aws': serializers.AmazonSMSerializer,
        'hcp': serializers.HashicorpKVSerializer
    }
    rbac_perms = {
        'POST': 'settings.change_vault'
    }

    def get_config(self, request, backend):
        serializer_class = self.backends_serializer.get(backend)
        if serializer_class is None:
            raise JMSException()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for k, v in data.items():
            if v:
                continue
            # 页面没有传递值, 从 settings 中获取
            data[k] = getattr(settings, k, None)
        return data

    def post(self, request, backend):
        config = self.get_config(request, backend)
        config['VAULT_ENABLED'] = settings.VAULT_ENABLED
        config['VAULT_BACKEND'] = backend
        try:
            client = get_vault_client(raise_exception=True, **config)
            ok, error = client.is_active()
        except Exception as e:
            ok, error = False, str(e)

        if ok:
            _status, msg = status.HTTP_200_OK, _('Test success')
        else:
            _status, msg = status.HTTP_400_BAD_REQUEST, error

        return Response(status=_status, data={'msg': msg})


class VaultSyncDataAPI(APIView):
    perm_model = Setting
    rbac_perms = {
        'POST': 'settings.change_vault'
    }

    def post(self, request, *args, **kwargs):
        task = self._run_task()
        return Response({'task': task.id}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _run_task():
        task = sync_secret_to_vault.delay()
        return task
