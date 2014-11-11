# coding: utf-8

from django import forms
from UserManage.models import Group


class GroupAddForm(forms.Form):
    name = forms.CharField(max_length=30)


class UserAddForm(forms.Form):
    username = forms.CharField(max_length=30,
                               widget=forms.TextInput(
                                   attrs={'class': 'form-control', 'placeholder': '用户名'}))
    password = forms.CharField(max_length=30,
                               widget=forms.PasswordInput(
                                   attrs={'class': 'form-control', 'placeholder': '密码'}))
    password_again = forms.CharField(max_length=30,
                                     widget=forms.PasswordInput(
                                         attrs={'class': 'form-control', 'placeholder': '确认密码'}))
    key_pass = forms.CharField(max_length=30, min_length=6,
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '密钥密码'}))
    key_pass_again = forms.CharField(max_length=30,
                                     widget=forms.PasswordInput(
                                         attrs={'class': 'form-control', 'placeholder': '确认密码'}))
    name = forms.CharField(max_length=30,
                           widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '姓名'}))
    group = forms.ModelMultipleChoiceField(queryset=Group.objects.all(),
                                           widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    is_admin = forms.BooleanField(required=False)
    is_superuser = forms.BooleanField(required=False)

    def clean_password_again(self):
        password = self.cleaned_data['password']
        password_again = self.cleaned_data['password_again']

        if password != password_again:
            raise forms.ValidationError('Password input twice not match. ')
        return password_again

    def clean_key_pass_again(self):
        key_pass = self.data['key_pass']
        key_pass_again = self.data['key_pass_again']
        if key_pass != key_pass_again:
            raise forms.ValidationError('Key Password input twice not match. ')
        if len(key_pass) < 6:
            raise forms.ValidationError('Key Password input twice not match. ')
        return key_pass_again