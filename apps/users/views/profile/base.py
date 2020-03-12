# ~*~ coding: utf-8 ~*~
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView

from common.utils import get_logger
from common.permissions import (
    PermissionsMixin, IsValidUser,
)
from ... import forms
from ...models import User


__all__ = ['UserProfileView', 'UserProfileUpdateView']
logger = get_logger(__name__)


class UserProfileView(PermissionsMixin, TemplateView):
    template_name = 'users/user_profile.html'
    permission_classes = [IsValidUser]

    def get_context_data(self, **kwargs):
        mfa_setting = settings.SECURITY_MFA_AUTH
        context = {
            'action': _('Profile'),
            'mfa_setting': mfa_setting if mfa_setting is not None else False,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserProfileUpdateView(PermissionsMixin, UpdateView):
    template_name = 'users/user_profile_update.html'
    model = User
    permission_classes = [IsValidUser]
    form_class = forms.UserProfileForm
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': _('User'),
            'action': _('Profile setting'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
