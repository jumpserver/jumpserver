# coding: utf-8
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.serializers import SecretReadableMixin
from .application import AppAccountSerializer, AppAccountSecretSerializer
from .. import models

__all__ = [
    'AppAccountHistorySerializer', 'AppAccountHistorySecretSerializer'
]


class AppAccountHistorySerializer(AppAccountSerializer):
    app_display = serializers.SerializerMethodField(label=_('Application display'))
    systemuser_display = serializers.SerializerMethodField(label=_('System user display'))

    class Meta:
        model = models.Account.history.model
        excludes = ['attrs']
        fields = AppAccountSerializer.Meta.fields
        fields = list(set(fields) - set(excludes)) + ['history_id']
        read_only_fields = fields

    @property
    def app(self):
        if isinstance(self.instance, models.Account.history.model):
            instance = self.instance.app
        else:
            instance = None
        return instance

    @staticmethod
    def get_app_display(instance):
        return instance.systemuser.name

    @staticmethod
    def get_systemuser_display(instance):
        if not instance.systemuser:
            return ''
        return str(instance.systemuser)

    def to_representation(self, instance):
        return super(AppAccountSerializer, self).to_representation(instance)


class AppAccountHistorySecretSerializer(SecretReadableMixin, AppAccountHistorySerializer):
    class Meta(AppAccountHistorySerializer.Meta):
        fields_backup = AppAccountSecretSerializer.Meta.fields_backup
        extra_kwargs = AppAccountSecretSerializer.Meta.extra_kwargs
