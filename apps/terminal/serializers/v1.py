# -*- coding: utf-8 -*-
#
import copy
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from common.fields.serializer import CustomMetaDictField
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


class ReplayStorageMetaDictField(CustomMetaDictField):
    type_map_fields = const.REPLAY_STORAGE_TYPE_MAP_FIELDS
    default_type = const.REPLAY_STORAGE_TYPE_SERVER
    need_convert_key = True


class BaseStorageSerializerMixin:
    type_map_fields = None

    def process_meta(self, instance, validated_data):
        new_meta = copy.deepcopy(validated_data.get('meta', {}))
        tp = validated_data.get('type', '')

        if tp != instance.type:
            return new_meta

        old_meta = instance.meta
        fields = self.type_map_fields.get(instance.type, [])
        for field in fields:
            if not field.get('write_only', False):
                continue
            field_name = field['name']
            new_value = new_meta.get(field_name, '')
            old_value = old_meta.get(field_name, '')
            field_value = new_value if new_value else old_value
            new_meta[field_name] = field_value

        return new_meta

    def update(self, instance, validated_data):
        meta = self.process_meta(instance, validated_data)
        validated_data['meta'] = meta
        return super().update(instance, validated_data)


class ReplayStorageSerializer(BaseStorageSerializerMixin,
                              serializers.ModelSerializer):

    meta = ReplayStorageMetaDictField()

    type_map_fields = const.REPLAY_STORAGE_TYPE_MAP_FIELDS

    class Meta:
        model = ReplayStorage
        fields = ['id', 'name', 'type', 'meta', 'comment']


class CommandStorageMetaDictField(CustomMetaDictField):
    type_map_fields = const.COMMAND_STORAGE_TYPE_MAP_FIELDS
    default_type = const.COMMAND_STORAGE_TYPE_SERVER
    need_convert_key = True


class CommandStorageSerializer(BaseStorageSerializerMixin,
                               serializers.ModelSerializer):

    meta = CommandStorageMetaDictField()

    type_map_fields = const.COMMAND_STORAGE_TYPE_MAP_FIELDS

    class Meta:
        model = CommandStorage
        fields = ['id', 'name', 'type', 'meta', 'comment']
