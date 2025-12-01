from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.status import HTTP_200_OK
from rbac.permissions import RBACPermission
from common.api import JMSModelViewSet
from ..serializers import AccessTokenSerializer

from oauth2_provider.models import get_access_token_model

AccessToken = get_access_token_model()

class AccessTokenViewSet(JMSModelViewSet):
    serializer_class = AccessTokenSerializer
    permission_classes = [RBACPermission]
    http_method_names = ['get', 'options', 'delete']
    rbac_perms = {
        'revoke': 'oauth2_provider.delete_accesstoken',
    }

    def get_queryset(self):
        return AccessToken.objects.filter(user=self.request.user).order_by('-created')

    @action(methods=['DELETE'], detail=True, url_path='revoke')
    def revoke(self, *args, **kwargs):
        token = AccessToken.objects.filter(id=kwargs['pk']).first()
        if not token or token.user != self.request.user:
            return Response({ "detail": _("Access token not found.") }, status=HTTP_200_OK)
        token = token.refresh_token or token
        token.revoke()
        return Response( {"detail": _("Token revoked successfully.")}, status=HTTP_200_OK)
