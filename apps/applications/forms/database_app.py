# coding: utf-8
#


from django import forms
from django.utils.translation import ugettext_lazy as _

from .. import models

__all__ = ['DatabaseAppMySQLForm']


class BaseDatabaseAppForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, max_length=128, strip=True, required=False,
        label=_("Password"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].widget.attrs['disabled'] = True

    class Meta:
        model = models.DatabaseApp
        fields = [
            'name', 'type', 'host', 'port', 'database', 'login_mode',
            'user', 'password', 'comment'
        ]


class DatabaseAppMySQLForm(BaseDatabaseAppForm):
    pass
