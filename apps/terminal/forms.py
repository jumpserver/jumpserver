# ~*~ coding: utf-8 ~*~
#

from django import forms
from django.utils.translation import ugettext_lazy as _

from .models import Terminal


class TerminalForm(forms.ModelForm):
    class Meta:
        model = Terminal
        fields = ['name', 'remote_addr', 'ssh_port', 'http_port', 'comment']
        help_texts = {
            'remote_addr': _('A unique addr of every terminal, user browser can arrive it'),
            'ssh_port': _("Coco ssh listen port"),
            'http_port': _("Coco http/ws listen port"),
        }
        widgets = {
            'name': forms.TextInput(attrs={'readonly': 'readonly'})
        }
