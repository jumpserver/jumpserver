import sys
from collections import defaultdict, OrderedDict

if sys.version_info.major >= 3 and sys.version_info.minor >= 10:
    from collections.abc import Iterable
else:
    from collections import Iterable
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import NOT_PROVIDED
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField, empty
from rest_framework.settings import api_settings
from rest_framework.utils import html

from common.db.fields import EncryptMixin
from common.serializers.fields import EncryptedField, LabeledChoiceField, ObjectRelatedField, LabelRelatedField

__all__ = [
    'BulkSerializerMixin', 'BulkListSerializerMixin',
    'CommonSerializerMixin', 'CommonBulkSerializerMixin',
    'SecretReadableMixin', 'CommonModelSerializer',
    'CommonBulkModelSerializer', 'ResourceLabelsMixin',
]


class SecretReadableMixin(serializers.Serializer):
    """ 加密字段 (EncryptedField) 可读性 """

    def __init__(self, *args, **kwargs):
        super(SecretReadableMixin, self).__init__(*args, **kwargs)
        if not hasattr(self, 'Meta') or not hasattr(self.Meta, 'extra_kwargs'):
            return
        extra_kwargs = self.Meta.extra_kwargs
        for field_name, serializer_field in self.fields.items():
            if not isinstance(serializer_field, EncryptedField):
                continue
            if field_name not in extra_kwargs:
                continue
            field_extra_kwargs = extra_kwargs[field_name]
            if 'write_only' not in field_extra_kwargs:
                continue
            serializer_field.write_only = field_extra_kwargs['write_only']


class BulkSerializerMixin(object):
    """
    Become rest_framework_bulk not support uuid as a primary key
    so rewrite it. https://github.com/miki725/django-rest-framework-bulk/issues/66
    """

    def to_internal_value(self, data):
        from rest_framework_bulk import BulkListSerializer
        ret = super(BulkSerializerMixin, self).to_internal_value(data)

        id_attr = getattr(self.Meta, 'update_lookup_field', 'id')
        if self.context.get('view'):
            request_method = getattr(getattr(self.context.get('view'), 'request'), 'method', '')
            # add update_lookup_field field back to validated data
            # since super by default strips out read-only fields
            # hence id will no longer be present in validated_data
            if all([
                isinstance(self.root, BulkListSerializer),
                id_attr,
                request_method in ('PUT', 'PATCH')
            ]):
                id_field = self.fields.get("id") or self.fields.get('pk')
                if data.get("id"):
                    id_value = id_field.to_internal_value(data.get("id"))
                else:
                    id_value = id_field.to_internal_value(data.get("pk"))
                ret[id_attr] = id_value
        return ret

    def run_validation(self, data=empty):
        """
        批量创建时，获取到的self.initial_data是list，
        所以想用一个属性来存放当前操作的数据集，在validate_field中使用
        :param data:
        :return:
        """
        # 只有批量创建的时候，才需要重写 initial_data
        if self.parent:
            self.initial_data = data
        return super().run_validation(data)

    @classmethod
    def many_init(cls, *args, **kwargs):
        from .common import AdaptedBulkListSerializer
        meta = getattr(cls, 'Meta', None)
        assert meta is not None, 'Must have `Meta`'
        if not hasattr(meta, 'list_serializer_class'):
            meta.list_serializer_class = AdaptedBulkListSerializer
        return super(BulkSerializerMixin, cls).many_init(*args, **kwargs)


class BulkListSerializerMixin:
    """
    Become rest_framework_bulk doing bulk update raise Exception:
    'QuerySet' object has no attribute 'pk' when doing bulk update
    so rewrite it .
    https://github.com/miki725/django-rest-framework-bulk/issues/68
    """

    def to_internal_value(self, data):
        """
        List of dicts of native values <- List of dicts of primitive datatypes.
        """
        if self.instance is None:
            return super().to_internal_value(data)

        if html.is_html_input(data):
            data = html.parse_html_list(data)

        if not isinstance(data, list):
            message = self.error_messages['not_a_list'].format(
                input_type=type(data).__name__
            )
            raise ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: [message]
            }, code='not_a_list')

        if not self.allow_empty and len(data) == 0:
            if self.parent and self.partial:
                raise SkipField()

            message = self.error_messages['empty']
            raise ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: [message]
            }, code='empty')

        ret = []
        errors = []

        for item in data:
            try:
                # prepare child serializer to only handle one instance
                if 'id' in item:
                    pk = item["id"]
                elif 'pk' in item:
                    pk = item["pk"]
                else:
                    raise ValidationError("id or pk not in data")
                child = self.instance.get(pk=pk)
                self.child.instance = child
                self.child.initial_data = item
                # raw
                validated = self.child.run_validation(item)
            except ValidationError as exc:
                errors.append(exc.detail)
            except ObjectDoesNotExist as e:
                errors.append(e)
            else:
                ret.append(validated)
                errors.append({})

        if any(errors):
            raise ValidationError(errors)

        return ret

    def create(self, validated_data):
        ModelClass = self.child.Meta.model
        use_model_bulk_create = getattr(self.child.Meta, 'use_model_bulk_create', False)
        model_bulk_create_kwargs = getattr(self.child.Meta, 'model_bulk_create_kwargs', {})

        if use_model_bulk_create:
            to_create = [
                ModelClass(**attrs) for attrs in validated_data
            ]
            objs = ModelClass._default_manager.bulk_create(
                to_create, **model_bulk_create_kwargs
            )
            return objs
        else:
            return super().create(validated_data)


class BaseDynamicFieldsPlugin:
    def __init__(self, serializer):
        self.serializer = serializer

    def can_dynamic(self):
        try:
            request = self.serializer.context['request']
            method = request.method
        except (AttributeError, TypeError, KeyError):
            # The serializer was not initialized with request context.
            return False

        if method != 'GET':
            return False
        return True

    def get_request(self):
        return self.serializer.context['request']

    def get_query_params(self):
        request = self.get_request()
        try:
            query_params = request.query_params
        except AttributeError:
            # DRF 2
            query_params = getattr(request, 'QUERY_PARAMS', request.GET)
        return query_params

    def get_exclude_field_names(self):
        return set()


class QueryFieldsMixin(BaseDynamicFieldsPlugin):
    # https://github.com/wimglenn/djangorestframework-queryfields/

    # If using Django filters in the API, these labels mustn't conflict with any model field names.
    include_arg_name = 'fields'
    exclude_arg_name = 'fields!'

    # Split field names by this string.  It doesn't necessarily have to be a single character.
    # Avoid RFC 1738 reserved characters i.e. ';', '/', '?', ':', '@', '=' and '&'
    delimiter = ','

    def get_exclude_field_names(self):
        query_params = self.get_query_params()
        includes = query_params.getlist(self.include_arg_name)
        include_field_names = {name for names in includes for name in names.split(self.delimiter) if name}

        excludes = query_params.getlist(self.exclude_arg_name)
        exclude_field_names = {name for names in excludes for name in names.split(self.delimiter) if name}

        if not include_field_names and not exclude_field_names:
            # No user fields filtering was requested, we have nothing to do here.
            return []

        serializer_field_names = set(self.serializer.fields)
        fields_to_drop = serializer_field_names & exclude_field_names

        if include_field_names:
            fields_to_drop |= serializer_field_names - include_field_names
        return fields_to_drop


class SizedModelFieldsMixin(BaseDynamicFieldsPlugin):
    arg_name = 'fields_size'

    def can_dynamic(self):
        if not hasattr(self.serializer, 'Meta'):
            return False
        can = super().can_dynamic()
        return can

    def get_exclude_field_names(self):
        query_params = self.get_query_params()
        size = query_params.get(self.arg_name)
        if not size:
            return []
        if size not in ['mini', 'small']:
            return []
        size_fields = getattr(self.serializer.Meta, 'fields_{}'.format(size), None)
        if not size_fields or not isinstance(size_fields, Iterable):
            return []
        serializer_field_names = set(self.serializer.fields)
        fields_to_drop = serializer_field_names - set(size_fields)
        return fields_to_drop


class DefaultValueFieldsMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_fields_default_value()

    def set_fields_default_value(self):
        if not hasattr(self, 'Meta'):
            return
        if not hasattr(self.Meta, 'model'):
            return
        model = self.Meta.model

        for name, serializer_field in self.fields.items():
            if serializer_field.default != empty or serializer_field.required:
                continue
            model_field = getattr(model, name, None)
            if model_field is None:
                continue
            if not hasattr(model_field, 'field') \
                    or not hasattr(model_field.field, 'default') \
                    or model_field.field.default == NOT_PROVIDED:
                continue
            if name == 'id':
                continue
            default = model_field.field.default

            if callable(default):
                default = default()
            if default == '':
                continue
            # print(f"Set default value: {name}: {default}")
            serializer_field.default = default


class DynamicFieldsMixin:
    """
    可以控制显示不同的字段，mini 最少，small 不包含关系
    """
    dynamic_fields_plugins = [QueryFieldsMixin, SizedModelFieldsMixin]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        exclude_field_names = set()
        for cls in self.dynamic_fields_plugins:
            plugin = cls(self)
            if not plugin.can_dynamic():
                continue
            exclude_field_names |= set(plugin.get_exclude_field_names())

        for field in exclude_field_names or []:
            self.fields.pop(field, None)


class RelatedModelSerializerMixin:
    serializer_related_field = ObjectRelatedField
    serializer_choice_field = LabeledChoiceField


class SomeFieldsMixin:
    instance: None
    initial_data: dict
    common_fields = (
        'comment', 'created_by', 'updated_by',
        'date_created', 'date_updated',
    )
    secret_fields = (
        'password', 'token', 'secret', 'key', 'private_key'
    )

    def get_initial_value(self, attr, default=None):
        value = self.initial_data.get(attr)
        if value is not None:
            return value
        if self.instance:
            value = getattr(self.instance, attr, default)
            return value
        return default

    @staticmethod
    def order_fields(fields):
        bool_fields = []
        datetime_fields = []
        other_fields = []

        for name, field in fields.items():
            to_add = (name, field)
            if isinstance(field, serializers.BooleanField):
                bool_fields.append(to_add)
            elif isinstance(field, serializers.DateTimeField):
                datetime_fields.append(to_add)
            else:
                other_fields.append(to_add)
        _fields = [*other_fields, *bool_fields, *datetime_fields]
        fields = OrderedDict()
        for name, field in _fields:
            fields[name] = field
        return fields

    def get_fields(self):
        fields = super().get_fields()
        fields = self.order_fields(fields)
        secret_readable = isinstance(self, SecretReadableMixin)

        for name, field in fields.items():
            if name == 'id':
                field.label = 'ID'
            elif isinstance(field, EncryptMixin) and not secret_readable:
                field.write_only = True
        return fields


class CommonSerializerMixin(DynamicFieldsMixin, RelatedModelSerializerMixin,
                            SomeFieldsMixin, DefaultValueFieldsMixin):
    pass


class CommonModelSerializer(CommonSerializerMixin, serializers.ModelSerializer):
    pass


class CommonBulkSerializerMixin(BulkSerializerMixin, CommonSerializerMixin):
    _save_kwargs = defaultdict(dict)


class CommonBulkModelSerializer(CommonBulkSerializerMixin, serializers.ModelSerializer):
    pass


class ResourceLabelsMixin(serializers.Serializer):
    labels = LabelRelatedField(many=True, label=_('Labels'), required=False, allow_null=True, source='res_labels')

    def update(self, instance, validated_data):
        labels = validated_data.pop('res_labels', None)
        res = super().update(instance, validated_data)
        if labels is not None:
            instance.res_labels.set(labels, bulk=False)
        return res

    def create(self, validated_data):
        labels = validated_data.pop('res_labels', None)
        instance = super().create(validated_data)
        if labels is not None:
            instance.res_labels.set(labels, bulk=False)
        return instance

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.prefetch_related('labels')
