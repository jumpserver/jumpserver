
# 添加自定义字段的 OpenAPI 扩展
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_basic_type
from rest_framework import serializers
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField, BitChoicesField


__all__ = [
    'ObjectRelatedFieldExtension', 'LabeledChoiceFieldExtension', 
    'BitChoicesFieldExtension', 'LabelRelatedFieldExtension',
    'DateTimeFieldExtension'
]


class ObjectRelatedFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 ObjectRelatedField 提供 OpenAPI schema
    """
    target_class = ObjectRelatedField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        # 获取字段的基本信息
        field_type = 'array' if field.many else 'object'
        
        if field_type == 'array':
            # 如果是多对多关系
            return {
                'type': 'array',
                'items': self._get_openapi_item_schema(field),
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }
        else:
            # 如果是一对一关系
            return {
                'type': 'object',
                'properties': self._get_openapi_properties_schema(field),
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }

    def _get_openapi_item_schema(self, field):
        """
        获取数组项的 OpenAPI schema
        """
        return self._get_openapi_object_schema(field)

    def _get_openapi_object_schema(self, field):
        """
        获取对象的 OpenAPI schema
        """
        properties = {}
        
        # 动态分析 attrs 中的属性类型
        for attr in field.attrs:
            # 尝试从 queryset 的 model 中获取字段信息
            field_type = self._infer_field_type(field, attr)
            properties[attr] = {
                'type': field_type,
                'description': f'{attr} field'
            }
        
        return {
            'type': 'object',
            'properties': properties,
            'required': ['id'] if 'id' in field.attrs else []
        }

    def _infer_field_type(self, field, attr_name):
        """
        智能推断字段类型
        """
        try:
            # 如果有 queryset，尝试从 model 中获取字段信息
            if hasattr(field, 'queryset') and field.queryset is not None:
                model = field.queryset.model
                if hasattr(model, '_meta') and hasattr(model._meta, 'fields'):
                    model_field = model._meta.get_field(attr_name)
                    if model_field:
                        return self._map_django_field_type(model_field)
        except Exception:
            pass
        
        # 如果没有 queryset 或无法获取字段信息，使用启发式规则
        return self._heuristic_field_type(attr_name)

    def _map_django_field_type(self, model_field):
        """
        将 Django 字段类型映射到 OpenAPI 类型
        """
        field_type = type(model_field).__name__
        
        # 整数类型
        if 'Integer' in field_type or 'BigInteger' in field_type or 'SmallInteger' in field_type or 'AutoField' in field_type:
            return 'integer'
        # 浮点数类型
        elif 'Float' in field_type or 'Decimal' in field_type:
            return 'number'
        # 布尔类型
        elif 'Boolean' in field_type:
            return 'boolean'
        # 日期时间类型
        elif 'DateTime' in field_type or 'Date' in field_type or 'Time' in field_type:
            return 'string'
        # 文件类型
        elif 'File' in field_type or 'Image' in field_type:
            return 'string'
        # 其他类型默认为字符串
        else:
            return 'string'

    def _heuristic_field_type(self, attr_name):
        """
        启发式推断字段类型
        """
        # 基于属性名的启发式规则
        
        if attr_name in ['is_active', 'enabled', 'visible'] or attr_name.startswith('is_'):
            return 'boolean'
        elif attr_name in ['count', 'number', 'size', 'amount']:
            return 'integer'
        elif attr_name in ['price', 'rate', 'percentage']:
            return 'number'
        else:
            # 默认返回字符串类型
            return 'string'

    def _get_openapi_properties_schema(self, field):
        """
        获取对象属性的 OpenAPI schema
        """
        return self._get_openapi_object_schema(field)['properties']


class LabeledChoiceFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 LabeledChoiceField 提供 OpenAPI schema
    """
    target_class = LabeledChoiceField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        if getattr(field, 'many', False):
            return {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'value': {'type': 'string'},
                        'label': {'type': 'string'}
                    }
                },
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }
        else:
            return {
                'type': 'object',
                'properties': {
                    'value': {'type': 'string'},
                    'label': {'type': 'string'}
                },
                'description': getattr(field, 'help_text', ''),
                'title': getattr(field, 'label', ''),
            }


class BitChoicesFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 BitChoicesField 提供 OpenAPI schema
    """
    target_class = BitChoicesField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        return {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'value': {'type': 'string'},
                    'label': {'type': 'string'}
                }
            },
            'description': getattr(field, 'help_text', ''),
            'title': getattr(field, 'label', ''),
        }


class LabelRelatedFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 LabelRelatedField 提供 OpenAPI schema
    """
    target_class = 'common.serializers.fields.LabelRelatedField'

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        # LabelRelatedField 返回一个包含 id, name, value, color 的对象
        return {
            'type': 'object',
            'properties': {
                'id': {
                    'type': 'string',
                    'description': 'Label ID'
                },
                'name': {
                    'type': 'string',
                    'description': 'Label name'
                },
                'value': {
                    'type': 'string',
                    'description': 'Label value'
                },
                'color': {
                    'type': 'string',
                    'description': 'Label color'
                }
            },
            'required': ['id', 'name', 'value'],
            'description': getattr(field, 'help_text', 'Label information'),
            'title': getattr(field, 'label', 'Label'),
        }


class DateTimeFieldExtension(OpenApiSerializerFieldExtension):
    """
    为 DateTimeField 提供自定义 OpenAPI schema
    修正 datetime 字段格式，使其符合实际返回格式 '%Y/%m/%d %H:%M:%S %z'
    而不是标准的 ISO 8601 格式 (date-time)
    """
    target_class = serializers.DateTimeField

    def map_serializer_field(self, auto_schema, direction):
        field = self.target
        
        # 获取字段的描述信息，确保始终是字符串类型
        help_text = getattr(field, 'help_text', None) or ''
        description = help_text if isinstance(help_text, str) else ''
        
        # 添加格式说明
        format_desc = 'Format: YYYY/MM/DD HH:MM:SS +TZ (e.g., 2023/10/01 12:00:00 +0800)'
        if description:
            description = f'{description} {format_desc}'
        else:
            description = format_desc
        
        # 返回字符串类型，不包含 format: date-time
        # 因为实际返回格式是 '%Y/%m/%d %H:%M:%S %z'，不是标准的 ISO 8601
        schema = {
            'type': 'string',
            'description': description,
            'title': getattr(field, 'label', '') or '',
            'example': '2023/10/01 12:00:00 +0800',
        }
        
        return schema