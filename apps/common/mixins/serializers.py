# -*- coding: utf-8 -*-
#

from rest_framework.utils import html
from rest_framework.settings import api_settings
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField

__all__ = ['BulkSerializerMixin', 'BulkListSerializerMixin']


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
                if 'id' in item.keys():
                    self.child.instance = self.instance.get(id=item['id']) if self.instance else None
                if 'pk' in item.keys():
                    self.child.instance = self.instance.get(id=item['pk']) if self.instance else None

                self.child.initial_data = item
                # raw
                validated = self.child.run_validation(item)
            except ValidationError as exc:
                errors.append(exc.detail)
            else:
                ret.append(validated)
                errors.append({})

        if any(errors):
            raise ValidationError(errors)

        return ret
