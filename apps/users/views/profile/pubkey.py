# ~*~ coding: utf-8 ~*~

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic.edit import UpdateView

from common.utils import get_logger, ssh_key_gen
from common.permissions import (
    PermissionsMixin, IsValidUser,
    UserCanUpdateSSHKey,
)
from ... import forms
from ...models import User

__all__ = [
    'UserPublicKeyUpdateView', 'UserPublicKeyGenerateView',
]

logger = get_logger(__name__)


class UserPublicKeyUpdateView(PermissionsMixin, UpdateView):
    template_name = 'users/user_pubkey_update.html'
    model = User
    form_class = forms.UserPublicKeyForm
    permission_classes = [IsValidUser, UserCanUpdateSSHKey]
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Public key update'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserPublicKeyGenerateView(PermissionsMixin, View):
    permission_classes = [IsValidUser]

    def get(self, request, *args, **kwargs):
        username = request.user.username
        private, public = ssh_key_gen(username=username, hostname='jumpserver')
        request.user.set_public_key(public)
        response = HttpResponse(private, content_type='text/plain')
        filename = "{0}-jumpserver.pem".format(username)
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response
