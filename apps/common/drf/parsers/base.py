import abc
import json
import codecs
from django.utils.translation import ugettext_lazy as _
from rest_framework.parsers import BaseParser
from rest_framework import status
from rest_framework.exceptions import ParseError, APIException
from common.utils import get_logger

logger = get_logger(__file__)


class CsvDataTooBig(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'csv_data_too_big'
    default_detail = _('The max size of CSV is %d bytes')


class JMSBaseParser(BaseParser):

    CSV_UPLOAD_MAX_SIZE = 1024 * 1024 * 10

    serializer_cls = None

    def check_content_length(self, meta):
        content_length = int(meta.get('CONTENT_LENGTH', meta.get('HTTP_CONTENT_LENGTH', 0)))
        if content_length > self.CSV_UPLOAD_MAX_SIZE:
            msg = CsvDataTooBig.default_detail % self.CSV_UPLOAD_MAX_SIZE
            logger.error(msg)
            raise CsvDataTooBig(msg)

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
    def _replace_chinese_quot(str_):
        trans_table = str.maketrans({
            '“': '"',
            '”': '"',
            '‘': '"',
            '’': '"',
            '\'': '"'
        })
        return str_.translate(trans_table)

    @classmethod
    def process_row(cls, row):
        """
        构建json数据前的行处理
        """
        _row = []

        for col in row:
            # 列表转换
            if isinstance(col, str) and col.startswith('[') and col.endswith(']'):
                col = cls._replace_chinese_quot(col)
                col = json.loads(col)
            # 字典转换
            if isinstance(col, str) and col.startswith("{") and col.endswith("}"):
                col = cls._replace_chinese_quot(col)
                col = json.loads(col)
            _row.append(col)
        return _row

    @staticmethod
    def process_row_data(row_data):
        """
        构建json数据后的行数据处理
        """
        _row_data = {}
        for k, v in row_data.items():
            if isinstance(v, list) or isinstance(v, dict)\
                    or isinstance(v, str) and k.strip() and v.strip():
                _row_data[k] = v
        return _row_data

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
            raise ParseError('CSV parse error!')

