# ~*~ coding: utf-8 ~*~
#

from django import forms
from django.utils.translation import ungettext_lazy as _

from .models import Terminal


class TerminalForm(forms.ModelForm):
    class Meta:
        model = Terminal
        fields = ['name', 'ip', 'is_active', 'type', 'url', 'comment']
        help_texts = {
            'url': 'Example: ssh://192.168.1.1:22 or http://jms.jumpserver.org, that user login'
        }

