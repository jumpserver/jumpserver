# ~*~ coding: utf-8 ~*~

from django.forms import ModelForm
from django import forms

from .models import User, UserGroup


# class UserLoginForm(ModelForm):
#     class Meta:
#         model = User
#         fields = [
#             "email", "password"
#         ]


class UserLoginForm(forms.Form):
    username = forms.CharField(label='用户名', max_length=100)
    password = forms.CharField(label='密码', widget=forms.PasswordInput, max_length=100)


class UserAddForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'name', 'email', 'groups', 'wechat',
            'phone', 'enable_otp', 'role', 'date_expired', 'comment',
        ]

        help_texts = {
            'username': '* required',
            'email': '* required',
        }

        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': '请选择用户组'}),
        }


class UserUpdateForm(ModelForm):
    class Meta:
        model = User
        fields = [
            'name', 'email', 'groups', 'wechat',
            'phone', 'enable_otp', 'role', 'date_expired', 'comment',
        ]

        help_texts = {
            'username': '* required',
            'email': '* required',
            'groups': '* required'
        }

        widgets = {
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'data-placeholder': '请选择用户组'}),
        }


class UserGroupForm(ModelForm):
    class Meta:
        model = UserGroup

        fields = [
            'name', 'comment',
        ]

        help_texts = {
            'name': '* required'
        }
