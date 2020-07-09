# ~*~ coding: utf-8 ~*~
#

import json
import chardet
import codecs
import unicodecsv

from django.utils.translation import ugettext as _
from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError, APIException
from rest_framework import status

from common.utils import get_logger

logger = get_logger(__file__)


class CsvDataTooBig(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'csv_data_too_big'
    default_detail = _('The max size of CSV is %d bytes')


class JMSCSVParser(BaseParser):
    """
    Parses CSV file to serializer data
    """
    CSV_UPLOAD_MAX_SIZE = 1024 * 1024 * 10

    media_type = 'text/csv'

    @staticmethod
    def _universal_newlines(stream):
        """
        保证在`通用换行模式`下打开文件
        """
        for line in stream.splitlines():
            yield line

    @staticmethod
    def _gen_rows(csv_data, charset='utf-8', **kwargs):
        csv_reader = unicodecsv.reader(csv_data, encoding=charset, **kwargs)
        for row in csv_reader:
            if not any(row):  # 空行
                continue
            yield row

    @staticmethod
    def _get_fields_map(serializer):
        fields_map = {}
        fields = serializer.fields
        fields_map.update({v.label: k for k, v in fields.items()})
        fields_map.update({k: k for k, _ in fields.items()})
        return fields_map

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
    def _process_row(cls, row):
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
    def _process_row_data(row_data):
        """
        构建json数据后的行数据处理
        """
        _row_data = {}
        for k, v in row_data.items():
            if isinstance(v, list) or isinstance(v, dict)\
                    or isinstance(v, str) and k.strip() and v.strip():
                _row_data[k] = v
        return _row_data

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        try:
            view = parser_context['view']
            meta = view.request.META
            serializer = view.get_serializer()
        except Exception as e:
            logger.debug(e, exc_info=True)
            raise ParseError('The resource does not support imports!')

        content_length = int(meta.get('CONTENT_LENGTH', meta.get('HTTP_CONTENT_LENGTH', 0)))
        if content_length > self.CSV_UPLOAD_MAX_SIZE:
            msg = CsvDataTooBig.default_detail % self.CSV_UPLOAD_MAX_SIZE
            logger.error(msg)
            raise CsvDataTooBig(msg)

        try:
            stream_data = stream.read()
            stream_data = stream_data.strip(codecs.BOM_UTF8)
            detect_result = chardet.detect(stream_data)
            encoding = detect_result.get("encoding", "utf-8")
            binary = self._universal_newlines(stream_data)
            rows = self._gen_rows(binary, charset=encoding)

            header = next(rows)
            fields_map = self._get_fields_map(serializer)
            header = [fields_map.get(name.strip('*'), '') for name in header]

            data = []
            for row in rows:
                row = self._process_row(row)
                row_data = dict(zip(header, row))
                row_data = self._process_row_data(row_data)
                data.append(row_data)
            return data
        except Exception as e:
            logger.error(e, exc_info=True)
            raise ParseError('CSV parse error!')
