# coding: utf-8
#


from django import forms
from django.utils.translation import ugettext_lazy as _

from .. import models

__all__ = ['DatabaseAppMySQLForm']


class BaseDatabaseAppForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].widget.attrs['disabled'] = True

    class Meta:
        model = models.DatabaseApp
        fields = [
            'name', 'type', 'host', 'port', 'database', 'comment'
        ]


class DatabaseAppMySQLForm(BaseDatabaseAppForm):
    pass
