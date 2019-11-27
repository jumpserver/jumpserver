# coding: utf-8
#

__all__ = ['TerminalForm']

from django import forms
from django.utils.translation import ugettext_lazy as _

from ..models import Terminal, ReplayStorage, CommandStorage


def get_all_command_storage():
    for c in CommandStorage.objects.all():
        yield (c.name, c.name)


def get_all_replay_storage():
    for r in ReplayStorage.objects.all():
        yield (r.name, r.name)


class TerminalForm(forms.ModelForm):
    command_storage = forms.ChoiceField(
        choices=get_all_command_storage,
        label=_("Command storage"),
        help_text=_("Command can store in server db or ES, default to server, more see docs"),
    )
    replay_storage = forms.ChoiceField(
        choices=get_all_replay_storage,
        label=_("Replay storage"),
        help_text=_("Replay file can store in server disk, AWS S3, Aliyun OSS, default to server, more see docs"),
    )

    class Meta:
        model = Terminal
        fields = [
            'name', 'remote_addr', 'comment',
            'command_storage', 'replay_storage',
        ]
