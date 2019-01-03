# -*- coding: utf-8 -*-
#
from django import forms

from assets.models import SystemUser
from .models import CommandExecution


class CommandExecutionForm(forms.ModelForm):
    class Meta:
        model = CommandExecution
        fields = ['run_as', 'command']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        run_as_field = self.fields.get('run_as')
        run_as_field.queryset = SystemUser.objects.all()
