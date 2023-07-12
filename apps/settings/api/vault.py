from django.utils.translation import gettext_lazy as _
from django.conf import settings
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.views import Response, APIView

from accounts.tasks.vault import sync_secret_to_vault
from accounts.backends import get_vault_client
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
        data = serializer.validated_data
        for k, v in data.items():
            if v:
                continue
            # 页面没有传递值, 从配置文件中获取
            data[k] = getattr(settings, k, None)

        vault_client = get_vault_client(**data)
        ok, error = vault_client.is_active()
        if ok:
            _status = status.HTTP_200_OK
            _data = {'msg': _('Test success')}
        else:
            _status = status.HTTP_400_BAD_REQUEST
            _data = {'error': error}
        return Response(status=_status, data=_data)


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

