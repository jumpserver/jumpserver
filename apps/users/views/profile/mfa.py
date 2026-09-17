# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals

from django.conf import settings
from django.utils.module_loading import import_string
from django.views.generic.base import TemplateView

from authentication.mfa.policy import get_allowed_mfa_types
from common.permissions import IsValidUser
from common.views.mixins import PermissionsMixin
from users.models import User

__all__ = ['MFASettingView']


class MFASettingView(PermissionsMixin, TemplateView):
    template_name = 'users/mfa_setting.html'
    permission_classes = [IsValidUser]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        mfa_backends = User.get_user_mfa_backends(user)
        allowed_mfa_types = get_allowed_mfa_types(user)
        unavailable_mfa_methods = []
        for backend_path in settings.MFA_BACKENDS:
            backend_class = import_string(backend_path)
            if backend_class.name not in allowed_mfa_types:
                continue
            if not backend_class.global_enabled():
                unavailable_mfa_methods.append(str(backend_class.display_name))

        context.update({
            'mfa_backends': mfa_backends,
            'unavailable_mfa_methods': ', '.join(unavailable_mfa_methods),
        })
        return context
