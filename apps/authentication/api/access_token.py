from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from oauth2_provider.models import get_access_token_model

from common.api import JMSModelViewSet
from rbac.permissions import RBACPermission
from ..serializers import AccessTokenSerializer


AccessToken = get_access_token_model()


class AccessTokenViewSet(JMSModelViewSet):
    """
    OAuth2 Access Token 管理视图集
    用户只能查看和撤销自己的 access token
    """
    serializer_class = AccessTokenSerializer
    permission_classes = [RBACPermission]
    http_method_names = ['get', 'options', 'delete']
    rbac_perms = {
        'revoke': 'oauth2_provider.delete_accesstoken',
    }

    def get_queryset(self):
        """只返回当前用户的 access token，按创建时间倒序"""
        return AccessToken.objects.filter(user=self.request.user).order_by('-created')

    @action(methods=['DELETE'], detail=True, url_path='revoke')
    def revoke(self, request, *args, **kwargs):
        """
        撤销 access token 及其关联的 refresh token
        如果 token 不存在或不属于当前用户，返回 404
        """
        token = get_object_or_404(
            AccessToken.objects.filter(user=request.user),
            id=kwargs['pk']
        )
        # 优先撤销 refresh token，会自动撤销关联的 access token
        token_to_revoke = token.refresh_token if token.refresh_token else token
        token_to_revoke.revoke()
        return Response(status=HTTP_204_NO_CONTENT)
