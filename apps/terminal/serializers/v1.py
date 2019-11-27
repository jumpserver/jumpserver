# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from ..models import (
    Terminal, Status, Session, Task, ReplayStorage, CommandStorage
)
from .. import const


class TerminalSerializer(serializers.ModelSerializer):
    session_online = serializers.SerializerMethodField()
    is_alive = serializers.BooleanField(read_only=True)

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'http_port', 'ssh_port',
            'comment', 'is_accepted', "is_active", 'session_online',
            'is_alive'
        ]

    @staticmethod
    def get_session_online(obj):
        return Session.objects.filter(terminal=obj, is_finished=False).count()


class SessionSerializer(BulkOrgResourceModelSerializer):
    command_amount = serializers.IntegerField(read_only=True)
    org_id = serializers.CharField(allow_blank=True)

    class Meta:
        model = Session
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            "id", "user", "asset", "system_user", "login_from",
            "login_from_display", "remote_addr", "is_finished",
            "has_replay", "can_replay", "protocol", "date_start", "date_end",
            "terminal", "command_amount",
        ]


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'terminal']
        model = Status


class TaskSerializer(BulkSerializerMixin, serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = AdaptedBulkListSerializer


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)


class ReplayStorageMetaDictField(serializers.DictField):

    @staticmethod
    def filter_attribute(attribute, instance):
        for field in const.REPLAY_STORAGE_TYPE_MAP_FIELDS[instance.type]:
            if field.get('write_only', False):
                attribute.pop(field['name'], None)
        return attribute

    def get_attribute(self, instance):
        """
        序列化时调用
        """
        attribute = super().get_attribute(instance)
        attribute = self.filter_attribute(attribute, instance)
        return attribute

    @staticmethod
    def convert_value(dictionary, value):
        tp = dictionary.get('type')
        _value = {}
        for k, v in value.items():
            prefix = '{}_'.format(tp)
            _k = k
            if k.lower().startswith(prefix):
                _k = k.lower().split(prefix, 1)[1]
            _k = _k.upper()
            _value[_k] = value[k]
        return _value

    @staticmethod
    def filter_value(dictionary, value):
        tp = dictionary.get('type', const.REPLAY_STORAGE_TYPE_SERVER)
        fields = const.REPLAY_STORAGE_TYPE_MAP_FIELDS.get(tp, [])
        fields_names = [field['name'] for field in fields]
        no_need_keys = [k for k in value.keys() if k not in fields_names]
        for k in no_need_keys:
            value.pop(k)
        return value

    def get_value(self, dictionary):
        """
        反序列化时调用
        """
        value = super().get_value(dictionary)
        value = self.convert_value(dictionary, value)
        value = self.filter_value(dictionary, value)
        return value


class ReplayStorageSerializer(serializers.ModelSerializer):
    meta = ReplayStorageMetaDictField()

    class Meta:
        model = ReplayStorage
        fields = ['id', 'name', 'type', 'meta']


class CommandStorageMetaDictField(serializers.DictField):

    @staticmethod
    def filter_attribute(attribute, instance):
        for field in const.COMMAND_STORAGE_TYPE_MAP_FIELDS[instance.type]:
            if field.get('write_only', False):
                attribute.pop(field['name'], None)
        return attribute

    def get_attribute(self, instance):
        """
        序列化时调用
        """
        attribute = super().get_attribute(instance)
        attribute = self.filter_attribute(attribute, instance)
        return attribute

    @staticmethod
    def convert_value(dictionary, value):
        tp = dictionary.get('type')
        _value = {}
        for k, v in value.items():
            prefix = '{}_'.format(tp)
            _k = k
            if k.lower().startswith(prefix):
                _k = k.lower().split(prefix, 1)[1]
            _k = _k.upper()
            _value[_k] = value[k]
        return _value

    @staticmethod
    def filter_value(dictionary, value):
        tp = dictionary.get('type', const.COMMAND_STORAGE_TYPE_SERVER)
        fields = const.COMMAND_STORAGE_TYPE_MAP_FIELDS.get(tp, [])
        fields_names = [field['name'] for field in fields]
        no_need_keys = [k for k in value.keys() if k not in fields_names]
        for k in no_need_keys:
            value.pop(k)
        return value

    def get_value(self, dictionary):
        """
        反序列化时调用
        """
        value = super().get_value(dictionary)
        value = self.convert_value(dictionary, value)
        value = self.filter_value(dictionary, value)
        return value


class CommandStorageSerializer(serializers.ModelSerializer):
    meta = CommandStorageMetaDictField()

    class Meta:
        model = CommandStorage
        fields = ['id', 'name', 'type', 'meta']
