# coding: utf-8

from jumpserver.conf import Config
from common.drf.serializers import DataSerializerGenerator

__all__ = ['SettingsSerializer', ]


class GenerateSerializerMeta(type):

    def __new__(cls, name, bases, attrs: dict):
        for name in Config.fieldsets:
            attrs['{0}SettingSerializer'.format(name)] = DataSerializerGenerator.generate_serializer_class(name)
        return type.__new__(cls, name, bases, attrs)


class SettingsSerializer(metaclass=GenerateSerializerMeta):
    # encrypt_fields 现在使用 write_only 来判断了
    pass
