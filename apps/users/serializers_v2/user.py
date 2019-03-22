# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from rest_framework import serializers
from ..models import User

from authentication.serializers import AccessKeySerializer

__all__ = ['ServiceAccountSerializer']


class ServiceAccountSerializer(serializers.ModelSerializer):
    access_key = AccessKeySerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'access_key']
        read_only_fields = ['access_key']

    def get_username(self):
        return self.initial_data.get('name')

    def get_email(self):
        name = self.initial_data.get('name')
        return '{}@serviceaccount.local'.format(name)

    def validate_name(self, name):
        email = self.get_email()
        username = self.get_username()
        if self.instance:
            users = User.objects.exclude(id=self.instance.id)
        else:
            users = User.objects.all()
        if users.filter(email=email) or \
                users.filter(username=username):
            raise serializers.ValidationError(_('name not unique'), code='unique')
        return name

    def save(self, **kwargs):
        self.validated_data['email'] = self.get_email()
        self.validated_data['username'] = self.get_username()
        self.validated_data['role'] = User.ROLE_APP
        return super().save(**kwargs)

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.create_access_key()
        return instance
