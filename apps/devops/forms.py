# ~*~ coding: utf-8 ~*~

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import *


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'name', 'desc', 'tags', 'ansible_role', 'system_user', 'admin_user'
        ]
        help_texts = {
            'deploy_path': '* required',
            'jrebel_path': '* required',
        }
        widgets = {
            'desc': forms.Textarea(),
        }
