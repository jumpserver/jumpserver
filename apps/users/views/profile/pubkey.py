# ~*~ coding: utf-8 ~*~

from django.http import HttpResponse
from django.views import View

from common.utils import get_logger, ssh_key_gen
from common.permissions import IsValidUser
from common.views.mixins import PermissionsMixin
from users.exceptions import CreateSSHKeyExceedLimit

__all__ = ['UserPublicKeyGenerateView']

logger = get_logger(__name__)


class UserPublicKeyGenerateView(PermissionsMixin, View):
    permission_classes = [IsValidUser]

    def get(self, request, *args, **kwargs):
        username = request.user.username
        key_name = request.GET.get('name', '')
        if not request.user.can_create_ssh_key():
            return HttpResponse(
                CreateSSHKeyExceedLimit().default_detail, status=400
            )
        private, public = ssh_key_gen(username=username, hostname='jumpserver')
        request.user.set_ssh_key(key_name, public, private)
        response = HttpResponse(private, content_type='text/plain')
        filename = "{0}-jumpserver.pem".format(username)
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response
