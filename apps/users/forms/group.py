# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from orgs.mixins.forms import OrgModelForm
from ..models import User, UserGroup

__all__ = ['UserGroupForm']


class UserGroupForm(OrgModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label=_("User"),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'users-select2',
                'data-placeholder': _('Select users')
            }
        ),
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        users_field = self.fields.get('users')
        if self.instance:
            users_field.initial = self.instance.users.all()
            users_field.queryset = self.instance.users.all()
        else:
            users_field.queryset = User.objects.none()

    def save(self, commit=True):
        raise Exception("Save by restful api")

    class Meta:
        model = UserGroup
        fields = [
            'name', 'users', 'comment',
        ]
