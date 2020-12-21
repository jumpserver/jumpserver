import abc
import json
import codecs
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from rest_framework.parsers import BaseParser
from rest_framework import status
from rest_framework.exceptions import ParseError, APIException
from common.utils import get_logger

logger = get_logger(__file__)


class FileContentOverflowedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'file_content_overflowed'
    default_detail = _('The file content overflowed (The maximum length `{}` bytes)')


class BaseFileParser(BaseParser):

    FILE_CONTENT_MAX_LENGTH = 1024 * 1024 * 10

    serializer_cls = None

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
        raise NotImplemented

    def get_column_titles(self, rows):
        return next(rows)

    def convert_to_field_names(self, column_titles):
        fields_map = {}
        fields = self.serializer_cls().fields
        fields_map.update({v.label: k for k, v in fields.items()})
        fields_map.update({k: k for k, _ in fields.items()})
        field_names = [
            fields_map.get(column_title.strip('*'), '')
            for column_title in column_titles
        ]
        return field_names

    @staticmethod
    def _replace_chinese_quote(s):
        trans_table = str.maketrans({
            '“': '"',
            '”': '"',
            '‘': '"',
            '’': '"',
            '\'': '"'
        })
        return s.translate(trans_table)

    @classmethod
    def process_row(cls, row):
        """
        构建json数据前的行处理
        """
        new_row = []
        for col in row:
            # 转换中文引号
            col = cls._replace_chinese_quote(col)
            # 列表/字典转换
            if isinstance(col, str) and (
                    (col.startswith('[') and col.endswith(']'))
                    or
                    (col.startswith("{") and col.endswith("}"))
            ):
                col = json.loads(col)
            new_row.append(col)
        return new_row

    def process_row_data(self, row_data):
        """
        构建json数据后的行数据处理
        """
        new_row_data = {}
        serializer_fields = self.serializer_cls().fields
        for k, v in row_data.items():
            if isinstance(v, list) or isinstance(v, dict) or isinstance(v, str) and k.strip() and v.strip():
                # 解决类似disk_info为字符串的'{}'的问题
                if not isinstance(v, str) and isinstance(serializer_fields[k], serializers.CharField):
                    v = str(v)
                new_row_data[k] = v
        return new_row_data

    def generate_data(self, fields_name, rows):
        data = []
        for row in rows:
            # 空行不处理
            if not any(row):
                continue
            row = self.process_row(row)
            row_data = dict(zip(fields_name, row))
            row_data = self.process_row_data(row_data)
            data.append(row_data)
        return data

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}

        try:
            view = parser_context['view']
            meta = view.request.META
            self.serializer_cls = view.get_serializer_class()
        except Exception as e:
            logger.debug(e, exc_info=True)
            raise ParseError('The resource does not support imports!')

        self.check_content_length(meta)

        try:
            stream_data = self.get_stream_data(stream)
            rows = self.generate_rows(stream_data)
            column_titles = self.get_column_titles(rows)
            field_names = self.convert_to_field_names(column_titles)
            data = self.generate_data(field_names, rows)
            return data
        except Exception as e:
            logger.error(e, exc_info=True)
            raise ParseError('Parse error! ({})'.format(self.media_type))

