import abc
import codecs
import json
import re

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ParseError, APIException
from rest_framework.parsers import BaseParser

from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.utils import get_logger

logger = get_logger(__file__)


class FileContentOverflowedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'file_content_overflowed'
    default_detail = _('The file content overflowed (The maximum length `{}` bytes)')


class BaseFileParser(BaseParser):
    FILE_CONTENT_MAX_LENGTH = 1024 * 1024 * 10

    serializer_cls = None
    serializer_fields = None
    obj_pattern = re.compile(r'^(.+)\(([a-z0-9-]+)\)$')

    def check_content_length(self, meta):
        content_length = int(meta.get('CONTENT_LENGTH', meta.get('HTTP_CONTENT_LENGTH', 0)))
        if content_length > self.FILE_CONTENT_MAX_LENGTH:
            msg = FileContentOverflowedError.default_detail.format(self.FILE_CONTENT_MAX_LENGTH)
            logger.error(msg)
            raise FileContentOverflowedError(msg)

    @staticmethod
    def get_stream_data(stream):
        stream_data = stream.read()
        stream_data = stream_data.strip(codecs.BOM_UTF8)
        return stream_data

    @abc.abstractmethod
    def generate_rows(self, stream_data):
        raise NotImplementedError

    def get_column_titles(self, rows):
        return next(rows)

    def convert_to_field_names(self, column_titles):
        fields_map = {}
        fields = self.serializer_fields
        for k, v in fields.items():
            # 资产平台的 id 是只读的, 导入更新资产平台会失败
            if v.read_only and k not in ['id', 'pk']:
                continue
            fields_map.update({
                v.label: k,
                k: k
            })
        lowercase_fields_map = {k.lower(): v for k, v in fields_map.items()}
        field_names = [
            lowercase_fields_map.get(column_title.strip('*').lower(), '')
            for column_title in column_titles
        ]
        return field_names

    @staticmethod
    def _replace_chinese_quote(s):
        if not isinstance(s, str):
            return s
        trans_table = str.maketrans({
            '“': '"',
            '”': '"',
            '‘': '"',
            '’': '"',
            '\'': '"'
        })
        return s.translate(trans_table)

    @classmethod
    def load_row(cls, row):
        """
        构建json数据前的行处理
        """
        new_row = []
        for col in row:
            # 转换中文引号
            col = cls._replace_chinese_quote(col)
            # 列表/字典转换
            if isinstance(col, str) and (
                    (col.startswith('[') and col.endswith(']')) or
                    (col.startswith("{") and col.endswith("}"))
            ):
                try:
                    col = json.loads(col)
                except json.JSONDecodeError as e:
                    logger.error('Json load error: ', e)
                    logger.error('col: ', col)
            new_row.append(col)
        return new_row

    def id_name_to_obj(self, v):
        if not v or not isinstance(v, str):
            return v
        matched = self.obj_pattern.match(v)
        if not matched:
            return v
        obj_name, obj_id = matched.groups()
        if len(obj_id) < 36:
            obj_id = int(obj_id)
        return {'pk': obj_id, 'name': obj_name}

    def parse_value(self, field, value):
        if value == '-' and field and field.allow_null:
            return None
        elif hasattr(field, 'to_file_internal_value'):
            value = field.to_file_internal_value(value)
        elif isinstance(field, serializers.BooleanField):
            value = value.lower() in ['true', '1', 'yes']
        elif isinstance(field, serializers.ChoiceField):
            value = value
        elif isinstance(field, ObjectRelatedField):
            if field.many:
                value = [self.id_name_to_obj(v) for v in value]
            else:
                value = self.id_name_to_obj(value)
        elif isinstance(field, LabeledChoiceField):
            value = self.id_name_to_obj(value)
            if isinstance(value, dict) and value.get('pk'):
                value = value.get('pk')
        elif isinstance(field, serializers.ListSerializer):
            value = [self.parse_value(field.child, v) for v in value]
        elif isinstance(field, serializers.Serializer):
            value = self.id_name_to_obj(value)
        elif isinstance(field, serializers.ManyRelatedField):
            value = [self.parse_value(field.child_relation, v) for v in value]
        elif isinstance(field, serializers.ListField):
            value = [self.parse_value(field.child, v) for v in value]

        return value

    def process_row_data(self, row_data):
        """
        构建json数据后的行数据处理
        """
        new_row = {}
        for k, v in row_data.items():
            field = self.serializer_fields.get(k)
            v = self.parse_value(field, v)
            new_row[k] = v
        return new_row

    def generate_data(self, fields_name, rows):
        data = []
        for row in rows:
            # 空行不处理
            if not any(row):
                continue
            row = self.load_row(row)
            row_data = dict(zip(fields_name, row))
            row_data = self.process_row_data(row_data)
            data.append(row_data)
        return data

    def parse(self, stream, media_type=None, parser_context=None):
        assert parser_context is not None, '`parser_context` should not be `None`'

        view = parser_context['view']
        request = view.request

        try:
            meta = request.META
            self.serializer_cls = view.get_serializer_class()
            self.serializer_fields = self.serializer_cls().fields
        except Exception as e:
            logger.debug(e, exc_info=True)
            raise ParseError('The resource does not support imports!')

        self.check_content_length(meta)
        try:
            stream_data = self.get_stream_data(stream)
            rows = self.generate_rows(stream_data)
            column_titles = self.get_column_titles(rows)
            field_names = self.convert_to_field_names(column_titles)

            # 给 `common.mixins.api.RenderToJsonMixin` 提供，暂时只能耦合
            column_title_field_pairs = list(zip(column_titles, field_names))
            column_title_field_pairs = [(k, v) for k, v in column_title_field_pairs if k and v]
            if not hasattr(request, 'jms_context'):
                request.jms_context = {}
            request.jms_context['column_title_field_pairs'] = column_title_field_pairs

            data = self.generate_data(field_names, rows)
            return data
        except Exception as e:
            logger.error(e, exc_info=True)
            raise ParseError(_('Parse file error: {}').format(e))
