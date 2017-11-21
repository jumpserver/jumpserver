# ~*~ coding: utf-8 ~*~

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import *


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'name', 'desc', 'tags', 'ansible_role'
        ]
        help_texts = {

        }
        widgets = {
            'desc': forms.Textarea(),
        }


class VariableForm(forms.ModelForm):
    class Meta:
        model = Variable
        fields = [
            'name', 'desc'
        ]
        help_texts = {

        }
        widgets = {
            'desc': forms.Textarea(),
        }