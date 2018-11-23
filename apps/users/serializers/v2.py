# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from ..models import User, AccessKey


class AccessKeySerializer(serializers.ModelSerializer):

    class Meta:
        model = AccessKey
        fields = ['id', 'secret']
        read_only_fields = ['id', 'secret']


class ServiceAccountRegistrationSerializer(serializers.ModelSerializer):
    access_key = AccessKeySerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'access_key']
        read_only_fields = ['id', 'access_key']

    def get_username(self):
        return self.initial_data.get('name')

    def get_email(self):
        name = self.initial_data.get('name')
        return '{}@serviceaccount.local'.format(name)

    def validate_name(self, name):
        email = self.get_email()
        username = self.get_username()
        if User.objects.filter(email=email) or \
                User.objects.filter(username=username):
            raise serializers.ValidationError('name not unique', code='unique')
        return name

    def create(self, validated_data):
        validated_data['email'] = self.get_email()
        validated_data['username'] = self.get_username()
        validated_data['role'] = User.ROLE_APP
        instance = super().create(validated_data)
        instance.create_access_key()
        return instance
