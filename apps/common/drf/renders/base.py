import abc
import io
import re
from datetime import datetime

import pyzipper
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.renderers import BaseRenderer
from rest_framework.utils import encoders, json

from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.utils import get_logger

logger = get_logger(__file__)


class BaseFileRenderer(BaseRenderer):
    # 渲染模版标识, 导入、导出、更新模版: ['import', 'update', 'export']
    template = 'export'
    serializer = None

    @staticmethod
    def _check_validation_data(data):
        detail_key = "detail"
        if detail_key in data:
            return False
        return True

    @staticmethod
    def _json_format_response(response_data):
        return json.dumps(response_data)

    def set_response_disposition(self, response):
        serializer = self.serializer
        if response and hasattr(serializer, 'Meta') and hasattr(serializer.Meta, "model"):
            filename_prefix = serializer.Meta.model.__name__.lower()
        else:
            filename_prefix = 'download'
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = "{}_{}.{}".format(filename_prefix, now, self.format)
        disposition = 'attachment; filename="{}"'.format(filename)
        response['Content-Disposition'] = disposition

    def get_rendered_fields(self):
        fields = self.serializer.fields
        if self.template == 'import':
            fields = [v for k, v in fields.items() if not v.read_only and k != "org_id" and k != 'id']
        elif self.template == 'update':
            fields = [v for k, v in fields.items() if not v.read_only and k != "org_id"]
        else:
            fields = [v for k, v in fields.items() if not v.write_only and k != "org_id"]

        meta = getattr(self.serializer, 'Meta', None)
        if meta:
            fields_unexport = getattr(meta, 'fields_unexport', [])
            fields = [v for v in fields if v.field_name not in fields_unexport]
        return fields

    @staticmethod
    def get_column_titles(render_fields):
        titles = []
        for field in render_fields:
            name = field.label
            if field.required:
                name = '*' + name
            titles.append(name)
        return titles

    def process_data(self, data):
        results = data['results'] if 'results' in data else data

        if isinstance(results, dict):
            results = [results]

        if self.template == 'import':
            results = [results[0]] if results else results
        else:
            # 限制数据数量
            results = results[:10000]
        # 会将一些 UUID 字段转化为 string
        results = json.loads(json.dumps(results, cls=encoders.JSONEncoder))
        return results

    @staticmethod
    def to_id_name(value):
        if value is None:
            return '-'
        pk = str(value.get('id', '') or value.get('pk', ''))
        name = value.get('display_name', '') or value.get('name', '')
        return '{}({})'.format(name, pk)

    @staticmethod
    def to_choice_name(value):
        if value is None:
            return '-'
        value = value.get('value', '')
        return value

    def render_value(self, field, value):
        if value is None:
            value = '-'
        elif hasattr(field, 'to_file_representation'):
            value = field.to_file_representation(value)
        elif isinstance(value, bool):
            value = 'Yes' if value else 'No'
        elif isinstance(field, LabeledChoiceField):
            value = value or {}
            value = '{}({})'.format(value.get('label'), value.get('value'))
        elif isinstance(field, ObjectRelatedField):
            if field.many:
                value = [self.to_id_name(v) for v in value]
            else:
                value = self.to_id_name(value)
        elif isinstance(field, serializers.ListSerializer):
            value = [self.render_value(field.child, v) for v in value]
        elif isinstance(field, serializers.Serializer) and value.get('id'):
            value = self.to_id_name(value)
        elif isinstance(field, serializers.ManyRelatedField):
            value = [self.render_value(field.child_relation, v) for v in value]
        elif isinstance(field, serializers.ListField):
            value = [self.render_value(field.child, v) for v in value]

        if not isinstance(value, str):
            value = json.dumps(value, cls=encoders.JSONEncoder, ensure_ascii=False)
        return str(value)

    def generate_rows(self, data, render_fields):
        for item in data:
            row = []
            for field in render_fields:
                value = item.get(field.field_name)
                value = self.render_value(field, value)
                row.append(value)
            yield row

    @abc.abstractmethod
    def initial_writer(self):
        raise NotImplementedError

    def write_column_titles(self, column_titles):
        self.write_row(column_titles)

    def write_rows(self, rows):
        for row in rows:
            self.write_row(row)

    @abc.abstractmethod
    def write_row(self, row):
        raise NotImplementedError

    @abc.abstractmethod
    def get_rendered_value(self):
        raise NotImplementedError

    def after_render(self):
        pass

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return bytes()

        if not self._check_validation_data(data):
            return self._json_format_response(data)

        try:
            renderer_context = renderer_context or {}
            request = renderer_context['request']
            response = renderer_context['response']
            view = renderer_context['view']
            self.template = request.query_params.get('template', 'export')
            self.serializer = view.get_serializer()
            self.set_response_disposition(response)
        except Exception as e:
            logger.debug(e, exc_info=True)
            value = 'The resource not support export!'.encode('utf-8')
            return value

        try:
            rendered_fields = self.get_rendered_fields()
            column_titles = self.get_column_titles(rendered_fields)
            data = self.process_data(data)
            rows = self.generate_rows(data, rendered_fields)
            self.initial_writer()
            self.write_column_titles(column_titles)
            self.write_rows(rows)
            self.after_render()
            value = self.get_rendered_value()
            if getattr(view, 'export_as_zip', False) and self.template == 'export':
                value = self.compress_into_zip_file(value, request, response)
        except Exception as e:
            logger.debug(e, exc_info=True)
            value = 'Render error! ({})'.format(self.media_type).encode('utf-8')
            return value
        return value

    def compress_into_zip_file(self, value, request, response):
        filename_pattern = re.compile(r'filename="([^"]+)"')
        content_disposition = response['Content-Disposition']
        match = filename_pattern.search(content_disposition)
        filename = match.group(1)
        response['Content-Disposition'] = content_disposition.replace(self.format, 'zip')

        contents_io = io.BytesIO()
        secret_key = request.user.secret_key
        if not secret_key:
            content = _("{} - The encryption password has not been set - "
                        "please go to personal information -> file encryption password "
                        "to set the encryption password").format(request.user.name)

            response['Content-Disposition'] = content_disposition.replace(self.format, 'txt')
            contents_io.write(content.encode('utf-8'))
            return contents_io.getvalue()

        with pyzipper.AESZipFile(
                contents_io, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES
        ) as zf:
            zf.setpassword(secret_key.encode('utf8'))
            zf.writestr(filename, value)
        return contents_io.getvalue()
