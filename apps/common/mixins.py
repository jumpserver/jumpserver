# coding: utf-8

from django.db import models
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_csv import renderers, parsers

from common.utils import get_logger

logger = get_logger(__file__)


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


class IDInCacheFiterMixin(object):
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.request.query_params.get('format') == 'csv':
            spm = self.request.query_params.get('spm', '')
            objs_id = cache.get(spm, [])
            if spm:
                return queryset.filter(id__in=objs_id)
            if not self.model:
                error = "'%s' should either include a `model` attribute, "
                logger.error(error % self.__class__.__name__)
                return []
            obj_default = self.model.objects.first()
            obj_id_default = [obj_default.id] if obj_default else []
            return queryset.filter(id__in=obj_id_default)
        return queryset


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


class FileViewMixin:
    model = ''
    csv_filename_prefix = ''

    def generate_filename(self):
        """
        根据csv_filename_prefix生成带有csv后缀的文件名
        """
        filename = '{}-{}.csv'.format(
            self.csv_filename_prefix,
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        return filename

    def get_parsers(self):
        """
        增加csv解析器
        """
        _parsers = api_settings.DEFAULT_PARSER_CLASSES
        _parsers.append(parsers.CSVParser)
        self.parser_classes = _parsers
        return super().get_parsers()

    def get_renderers(self):
        """
        如果是导出和下载模板，使用CSV渲染器
        """
        if self.request.query_params.get('format', '') in ('csv', 'CSV'):
            self.renderer_classes = (renderers.CSVStreamingRenderer,)
        return super().get_renderers()

    def get_renderer_context(self):
        """
        如果是导出和下载模板请求，构造csv表头
        csv中英文表头
        """
        context = super().get_renderer_context()
        fields = self.get_serializer_class()().get_fields()

        header = [field for field in fields]
        if self.request.query_params.get('spm'):
            labels = dict([(k, v.label if v.label else k) for k, v in fields.items()])
            context.update({'labels': labels})

        context.update({'header': header})
        return context

    def finalize_response(self, request, response, *args, **kwargs):
        """
        构造导出csv的文件名
        """
        if request._request.GET.get('format', '') == 'csv':
            response['Content-Disposition'] = 'attachment; filename="%s"' \
                                              % self.generate_filename()
        return super().finalize_response(request, response, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        bulk = isinstance(request.data, list)

        if not bulk:
            return super().create(request, *args, **kwargs)
        else:
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            try:
                self.perform_bulk_create(serializer)
            except Exception as e:
                return Response(str(e), status=status.HTTP_409_CONFLICT)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

