# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import NodePermission


class AssetPermissionForm(forms.ModelForm):
    class Meta:
        model = NodePermission
        fields = [
            'node', 'user_group', 'system_user', 'is_active',
            'date_expired', 'comment',
        ]
        widgets = {
            'node': forms.Select(
                attrs={'style': 'display:none'}
            ),
            'user_group': forms.Select(
                attrs={'class': 'select2', 'data-placeholder': _("User group")}
            ),
            'system_user': forms.Select(
                attrs={'class': 'select2', 'data-placeholder': _('System user')}
            ),
        }

    def clean_system_user(self):
        return self.cleaned_data['system_user']
