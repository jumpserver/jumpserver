# coding: utf-8
#

import json
from django import forms
from django.db import transaction
from django.conf import settings

from ..models import Setting
from common.fields import FormEncryptMixin

__all__ = ['BaseForm']


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            value = getattr(settings, name, None)
            if value is None:  # and django_value is None:
                continue

            if value is not None:
                if isinstance(value, dict):
                    value = json.dumps(value)
                initial_value = value
            else:
                initial_value = ''
            field.initial = initial_value

    def save(self, category="default"):
        if not self.is_bound:
            raise ValueError("Form is not bound")

        # db_settings = Setting.objects.all()
        if not self.is_valid():
            raise ValueError(self.errors)

        with transaction.atomic():
            for name, value in self.cleaned_data.items():
                field = self.fields[name]
                if isinstance(field.widget, forms.PasswordInput) and not value:
                    continue
                # if value == getattr(settings, name):
                #     continue

                encrypted = True if isinstance(field, FormEncryptMixin) else False
                try:
                    setting = Setting.objects.get(name=name)
                except Setting.DoesNotExist:
                    setting = Setting()
                setting.name = name
                setting.category = category
                setting.encrypted = encrypted
                setting.cleaned_value = value
                setting.save()

