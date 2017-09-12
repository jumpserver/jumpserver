# ~*~ coding: utf-8 ~*~

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import *


class InstallUpdateForm(forms.ModelForm):
    class Meta:
        model = InstallTemplate
        fields = [
            'hybris_path', 'deploy_path', 'deploy_jrebel', 'jrebel_path', 'db_driver_url',
        ]
        help_texts = {
            'deploy_path': '* required',
            'jrebel_path': '* required',
        }
        widgets = {
            'hybris_path': forms.TextInput(attrs={'readonly': True}),
        }
