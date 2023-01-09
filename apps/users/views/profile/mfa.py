# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals
from django.views.generic.base import TemplateView

from common.permissions import IsValidUser
from common.views.mixins import PermissionsMixin
from users.models import User

__all__ = ['MFASettingView']


class MFASettingView(PermissionsMixin, TemplateView):
    template_name = 'users/mfa_setting.html'
    permission_classes = [IsValidUser]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mfa_backends = User.get_user_mfa_backends(self.request.user)
        context.update({
            'mfa_backends': mfa_backends,
        })
        return context
