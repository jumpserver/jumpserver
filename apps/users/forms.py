# ~*~ coding: utf-8 ~*~

from django.forms import ModelForm
from django import forms

from .models import User, UserGroup


class UserForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'name', 'email', 'groups', 'wechat', 'avatar',
            'phone', 'enable_2FA', 'role', 'date_expired', 'comment',
        ]
        # widgets = {
        #     'groups': forms.SelectMultiple(attrs={'class': 'chosen-select'})
        # }


