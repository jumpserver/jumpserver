# -*- coding: utf-8 -*-
#
from collections import Iterable

from django.db.models import Prefetch, F
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.utils import html
from rest_framework.settings import api_settings
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField, empty

__all__ = ['BulkSerializerMixin', 'BulkListSerializerMixin', 'CommonSerializerMixin', 'CommonBulkSerializerMixin']


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
            if all((isinstance(self.root, BulkListSerializer),
                    id_attr,
                    request_method in ('PUT', 'PATCH'))):
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


class BulkListSerializerMixin(object):
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
        if not self.instance:
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
                child = self.instance.get(id=pk) if self.instance else None
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


class DynamicFieldsMixin:
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


class EagerLoadQuerySetFields:
    def setup_eager_loading(self, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related(
            Prefetch('nodes'),
            Prefetch('labels'),
        ).select_related('admin_user', 'domain', 'platform') \
         .annotate(platform_base=F('platform__base'))
        return queryset


class CommonSerializerMixin(DynamicFieldsMixin):
    pass


class CommonBulkSerializerMixin(BulkSerializerMixin, CommonSerializerMixin):
    pass
