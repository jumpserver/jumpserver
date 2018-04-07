# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import AssetPermission


class AssetPermissionForm(forms.ModelForm):
    class Meta:
        model = AssetPermission
        exclude = (
            'id', 'date_created', 'created_by'
        )
        widgets = {
            'users': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("User")}
            ),
            'user_groups': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("User group")}
            ),
            'assets': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("Asset")}
            ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _("Node")}
            ),
            'system_users': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('System user')}
            ),
        }
        labels = {
            'nodes': _("Node"),
        }
