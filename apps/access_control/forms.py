#  coding: utf-8
#

from django.utils.translation import ugettext as _
from django import forms

from orgs.mixins.forms import OrgModelForm

from .models import AccessControl


class AccessControlForm(OrgModelForm):
    default_initial_data = {}
    date_from = forms.DateTimeField(label=_('Date from'))
    date_to = forms.DateTimeField(label=_('Date to'))

    def initial_default(self):
        for name, value in self.default_initial_data.items():
            field = self.fields.get(name)
            if not field:
                continue
            field.initial = value

    class Meta:
        model = AccessControl
        fields = [
            'id', 'name', 'ips', 'date_from', 'date_to', 'users'
        ]
        widgets = {
            'users': forms.SelectMultiple(attrs={
                'class': 'users-select2', 'data-placeholder': _('Users')
            }),
        }
