# coding: utf-8
#


from django import forms
from django.utils.translation import ugettext_lazy as _

from terminal.models import CommandStorage


__all__ = [
    'CommandStorageTypeESForm'
]


class BaseCommandStorageForm(forms.ModelForm):
    disable_fields = ['type']

    def __init__(self, *args, **kwargs):
        super(BaseCommandStorageForm, self).__init__(*args, **kwargs)
        for field in self.disable_fields:
            self.fields[field].widget.attrs['disabled'] = True

    class Meta:
        model = CommandStorage
        fields = ['name', 'type']


class CommandStorageTypeESForm(BaseCommandStorageForm):
    es_hosts = forms.CharField(
        max_length=128, label=_('Hosts'), required=False,
        help_text=_(
            """
            Tips: If there are multiple hosts, separate them with a comma (,) 
            <br>
            eg: http://www.jumpserver.a.com,http://www.jumpserver.b.com
            """
        )
    )
    es_index = forms.CharField(
        max_length=128, label=_('Index'), required=False
    )
    es_doc_type = forms.CharField(
        max_length=128, label=_('Doc type'), required=False
    )
