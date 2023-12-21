from rest_framework import status
from rest_framework.views import Response, APIView
from accounts.tasks.ris import sync_secret_from_ris
from settings.models import Setting


class RisSyncDataAPI(APIView):
    perm_model = Setting
    rbac_perms = {
        'POST': 'settings.change_ris'
    }

    def post(self, request, *args, **kwargs):
        task = self._run_task()
        return Response({'task': task.id}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _run_task():
        task = sync_secret_from_ris.delay()
        return task
