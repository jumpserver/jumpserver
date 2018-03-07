# ~*~ coding: utf-8 ~*~
#

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .models import Terminal


def get_all_command_storage():
    # storage_choices = []
    from common.models import Setting
    Setting.refresh_all_settings()
    for k, v in settings.TERMINAL_COMMAND_STORAGE.items():
        yield (k, k)


def get_all_replay_storage():
    # storage_choices = []
    from common.models import Setting
    Setting.refresh_all_settings()
    for k, v in settings.TERMINAL_REPLAY_STORAGE.items():
        yield (k, k)


class TerminalForm(forms.ModelForm):
    command_storage = forms.ChoiceField(
        choices=get_all_command_storage(),
        label=_("Command storage")
    )
    replay_storage = forms.ChoiceField(
        choices=get_all_replay_storage(),
        label=_("Replay storage")
    )

    class Meta:
        model = Terminal
        fields = [
            'name', 'remote_addr', 'ssh_port', 'http_port', 'comment',
            'command_storage', 'replay_storage',
        ]
        help_texts = {
            'ssh_port': _("Coco ssh listen port"),
            'http_port': _("Coco http/ws listen port"),
        }
