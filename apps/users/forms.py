# ~*~ coding: utf-8 ~*~

from django.forms import ModelForm

from .models import User, UserGroup


class UserForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'name', 'email', 'groups', 'wechat',
            'phone', 'enable_2FA', 'role', 'comment',
        ]

