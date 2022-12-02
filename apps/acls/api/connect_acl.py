from rest_framework.views import APIView
from rest_framework import status
from django.http.response import JsonResponse
from django.utils.translation import ugettext_lazy as _

from common.drf.api import JMSBulkModelViewSet
from common.const.choices import ConnectMethodChoices
from ..models import ConnectACL
from .. import serializers

__all__ = ['ConnectACLViewSet', 'ConnectMethodsAPI', 'ConnectMethodPermissionsAPI']


class ConnectACLViewSet(JMSBulkModelViewSet):
    queryset = ConnectACL.objects.all()
    filterset_fields = ('name', )
    search_fields = ('name',)
    serializer_class = serializers.ConnectACLSerializer


class ConnectMethodsAPI(APIView):
    rbac_perms = {
        'GET': 'acls.view_connnectacl',
    }

    @staticmethod
    def get(request, *args, **kwargs):
        data = []
        for m in ConnectMethodChoices.choices:
            data.append({'label': m[1], 'value': m[0]})
        return JsonResponse(data, safe=False)


class ConnectMethodPermissionsAPI(APIView):
    rbac_perms = {
        'GET': 'acls.view_connnectacl',
    }

    @staticmethod
    def get(request, *args, **kwargs):
        login_type = request.query_params.get('login_type')
        if not login_type:
            rules = ConnectACL().all_rules(request.user)
            return JsonResponse({'rules': rules})

        acl = ConnectACL.match(request.user, login_type)
        if acl:
            err = _('The current user is not allowed to login in this way')
            return JsonResponse({'error': err})
        else:
            return JsonResponse({'msg': 'ok'})

