# -*- coding: utf-8 -*-
#
import copy
from rest_framework import serializers

from common.fields.serializer import CustomMetaDictField
from ..models import ReplayStorage, CommandStorage
from .. import const


class ReplayStorageMetaDictField(CustomMetaDictField):
    type_fields_map = const.REPLAY_STORAGE_TYPE_FIELDS_MAP
    default_type = const.REPLAY_STORAGE_TYPE_SERVER
    convert_key_remove_type_prefix = True
    convert_key_to_upper = True


class BaseStorageSerializerMixin:
    type_fields_map = None

    def process_meta(self, instance, validated_data):
        new_meta = copy.deepcopy(validated_data.get('meta', {}))
        tp = validated_data.get('type', '')

        if tp != instance.type:
            return new_meta

        old_meta = instance.meta
        fields = self.type_fields_map.get(instance.type, [])
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

    type_fields_map = const.REPLAY_STORAGE_TYPE_FIELDS_MAP

    class Meta:
        model = ReplayStorage
        fields = ['id', 'name', 'type', 'meta', 'comment']


class CommandStorageMetaDictField(CustomMetaDictField):
    type_fields_map = const.COMMAND_STORAGE_TYPE_FIELDS_MAP
    default_type = const.COMMAND_STORAGE_TYPE_SERVER
    convert_key_remove_type_prefix = True
    convert_key_to_upper = True


class CommandStorageSerializer(BaseStorageSerializerMixin,
                               serializers.ModelSerializer):

    meta = CommandStorageMetaDictField()

    type_fields_map = const.COMMAND_STORAGE_TYPE_FIELDS_MAP

    class Meta:
        model = CommandStorage
        fields = ['id', 'name', 'type', 'meta', 'comment']
