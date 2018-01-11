# -*- coding: utf-8 -*-
#
import json

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.db import transaction

from .models import Setting


def to_model_value(value):
    try:
        return json.dumps(value)
    except json.JSONDecodeError:
        return None


def to_form_value(value):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return ''


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            settings = Setting.objects.all()
            for name, field in self.fields.items():
                db_value = getattr(settings, name).value
                if db_value:
                    field.initial = to_form_value(db_value)

    def save(self):
        if not self.is_bound:
            raise ValueError("Form is not bound")

        if self.is_valid():
            with transaction.atomic():
                for name, value in self.cleaned_data.items():
                    field = self.fields[name]
                    if isinstance(field.widget, forms.PasswordInput) and not value:
                        continue
                    defaults = {
                        'name': name,
                        'value': to_model_value(value)
                    }
                    Setting.objects.update_or_create(defaults=defaults, name=name)
        else:
            raise ValueError(self.errors)


class EmailSettingForm(BaseForm):
    EMAIL_HOST = forms.CharField(
        max_length=1024, label=_("SMTP host"), initial='smtp.jumpserver.org'
    )
    EMAIL_PORT = forms.CharField(max_length=5, label=_("SMTP port"), initial=25)
    EMAIL_HOST_USER = forms.CharField(
        max_length=128, label=_("SMTP user"), initial='noreply@jumpserver.org'
    )
    EMAIL_HOST_PASSWORD = forms.CharField(
        max_length=1024, label=_("SMTP password"), widget=forms.PasswordInput,
        required=False, help_text=_("Some provider use token except password")
    )
    EMAIL_USE_SSL = forms.BooleanField(
        label=_("Use SSL"), initial=False, required=False,
        help_text=_("If SMTP port is 465, may be select")
    )
    EMAIL_USE_TLS = forms.BooleanField(
        label=_("Use TLS"), initial=False, required=False,
        help_text=_("If SMTP port is 587, may be select")
    )
