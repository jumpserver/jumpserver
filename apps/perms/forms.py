# ~*~ coding: utf-8 ~*~

from __future__ import absolute_import, unicode_literals
from django import forms
from django.utils.translation import ugettext_lazy as _

from .hands import User
from .models import AssetPermission


class AssetPermissionForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.exclude(role=User.ROLE_APP),
        label=_("User"),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select users')
            }
        ),
        required=False,
    )

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

    def clean_user_groups(self):
        users = self.cleaned_data.get('users')
        user_groups = self.cleaned_data.get('user_groups')

        if not users and not user_groups:
            raise forms.ValidationError(
                _("User or group at least one required"))
        return self.cleaned_data["user_groups"]

    def clean_asset_groups(self):
        assets = self.cleaned_data.get('assets')
        asset_groups = self.cleaned_data.get('asset_groups')

        if not assets and not asset_groups:
            raise forms.ValidationError(
                _("Asset or group at least one required"))

        return self.cleaned_data["asset_groups"]
