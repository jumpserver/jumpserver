# coding: utf-8

from django import forms
from UserManage.models import Group


class GroupAddForm(forms.Form):
    name = forms.CharField(max_length=30)


class UserAddForm(forms.Form):
    username = forms.CharField(max_length=30,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '用户名'}))
    password = forms.CharField(max_length=30,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '密码'}))
    password_again = forms.CharField(max_length=30,
                                     widget=forms.PasswordInput(
                                         attrs={'class': 'form-control', 'placeholder': '确认密码'}))
    key_pass = forms.CharField(max_length=30,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '密钥密码'}))
    key_pass_again = forms.CharField(max_length=30,
                                     widget=forms.PasswordInput(
                                         attrs={'class': 'form-control', 'placeholder': '确认密码'}))
    name = forms.CharField(max_length=30,
                           widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '姓名'}))
    group = forms.ModelMultipleChoiceField(queryset=Group.objects.all(),
                                           widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    is_admin = forms.BooleanField()
    is_superuser = forms.BooleanField()


