# coding: utf-8

from django.db import models
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from rest_framework.utils import html
from rest_framework.settings import api_settings
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField

from .const import KEY_CACHE_RESOURCES_ID


class NoDeleteQuerySet(models.query.QuerySet):

    def delete(self):
        return self.update(is_discard=True, discard_time=timezone.now())


class NoDeleteManager(models.Manager):

    def get_all(self):
        return NoDeleteQuerySet(self.model, using=self._db)

    def get_queryset(self):
        return NoDeleteQuerySet(self.model, using=self._db).filter(is_discard=False)

    def get_deleted(self):
        return NoDeleteQuerySet(self.model, using=self._db).filter(is_discard=True)


class NoDeleteModelMixin(models.Model):
    is_discard = models.BooleanField(verbose_name=_("is discard"), default=False)
    discard_time = models.DateTimeField(verbose_name=_("discard time"), null=True, blank=True)

    objects = NoDeleteManager()

    class Meta:
        abstract = True

    def delete(self):
        self.is_discard = True
        self.discard_time = timezone.now()
        return self.save()


class JSONResponseMixin(object):
    """JSON mixin"""
    @staticmethod
    def render_json_response(context):
        return JsonResponse(context)


class IDInFilterMixin(object):
    def filter_queryset(self, queryset):
        queryset = super(IDInFilterMixin, self).filter_queryset(queryset)
        id_list = self.request.query_params.get('id__in')
        if id_list:
            import json
            try:
                ids = json.loads(id_list)
            except Exception as e:
                return queryset
            if isinstance(ids, list):
                queryset = queryset.filter(id__in=ids)
        return queryset


class IDInCacheFilterMixin(object):

    def filter_queryset(self, queryset):
        queryset = super(IDInCacheFilterMixin, self).filter_queryset(queryset)
        spm = self.request.query_params.get('spm')
        cache_key = KEY_CACHE_RESOURCES_ID.format(spm)
        resources_id = cache.get(cache_key)
        if resources_id and isinstance(resources_id, list):
            queryset = queryset.filter(id__in=resources_id)
        return queryset


class IDExportFilterMixin(object):
    def filter_queryset(self, queryset):
        # 下载导入模版
        if self.request.query_params.get('template') == 'import':
            return []
        else:
            return super(IDExportFilterMixin, self).filter_queryset(queryset)


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
                id_field = self.fields[id_attr]
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


class DatetimeSearchMixin:
    date_format = '%Y-%m-%d'
    date_from = date_to = None

    def get_date_range(self):
        date_from_s = self.request.GET.get('date_from')
        date_to_s = self.request.GET.get('date_to')

        if date_from_s:
            date_from = timezone.datetime.strptime(date_from_s, self.date_format)
            tz = timezone.get_current_timezone()
            self.date_from = tz.localize(date_from)
        else:
            self.date_from = timezone.now() - timezone.timedelta(7)

        if date_to_s:
            date_to = timezone.datetime.strptime(
                date_to_s + ' 23:59:59', self.date_format + ' %H:%M:%S'
            )
            self.date_to = date_to.replace(
                tzinfo=timezone.get_current_timezone()
            )
        else:
            self.date_to = timezone.now()

    def get(self, request, *args, **kwargs):
        self.get_date_range()
        return super().get(request, *args, **kwargs)
