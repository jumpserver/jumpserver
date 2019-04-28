# ~*~ coding: utf-8 ~*~
#

import unicodecsv

from rest_framework.parsers import BaseParser

from ..utils import get_logger

logger = get_logger(__file__)


def universal_newlines(stream):
    """
    保证在通用换行模式下打开文件
    """
    for line in stream.splitlines():
        yield line


def generate_rows(csv_data, charset='utf-8', **kwargs):
    csv_reader = unicodecsv.reader(csv_data, encoding=charset, **kwargs)
    for row in csv_reader:
        # 空行
        if not any(row):
            continue
        yield row


class JMSCSVParser(BaseParser):
    """
    Parses CSV file to serializer data
    """

    media_type = 'text/csv'
    view = None

    @staticmethod
    def _get_data(header, rows):
        data = []
        for row in rows:
            row_data = dict(zip(header, row))
            row_data = {
                k: v for k, v in row_data.items() if k.strip() and v.strip()
            }
            data.append(row_data)
        return data

    def _get_header_fields_map(self):
        fields_map = {}
        serializer = self.view.get_serializer_class()()
        fields = serializer.get_fields()
        fields_map.update({v.label: k for k, v in fields.items()})
        fields_map.update({k: k for k, _ in fields.items()})
        return fields_map

    def _convert_header(self, header):
        fields_map = self._get_header_fields_map()
        _header = [fields_map.get(name, '') for name in header]
        return _header

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', 'utf-8')
        self.view = parser_context.get("view")
        try:
            stream_data = stream.read()
            binary = universal_newlines(stream_data)
            rows = generate_rows(binary, charset=encoding)
            header = next(rows)
            header = self._convert_header(header)
            data = self._get_data(header, rows)
            return data
        except Exception as e:
            logger.debug(e, exc_info=True)
