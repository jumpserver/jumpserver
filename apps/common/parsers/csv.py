# ~*~ coding: utf-8 ~*~
#

import unicodecsv

from rest_framework.parsers import BaseParser

from ..utils import get_logger

logger = get_logger(__file__)


def universal_newlines(stream):
    """
    保证在`通用换行模式`下打开文件
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
    serializer = None

    @staticmethod
    def _get_fields_map(serializer):
        fields_map = {}
        fields = serializer.get_fields()
        fields_map.update({v.label: k for k, v in fields.items()})
        fields_map.update({k: k for k, _ in fields.items()})
        return fields_map

    @staticmethod
    def _gen_rows(csv_data, charset='utf-8', **kwargs):
        csv_reader = unicodecsv.reader(csv_data, encoding=charset, **kwargs)
        for row in csv_reader:
            if not any(row):  # 空行
                continue

            yield row

    @staticmethod
    def _universal_newlines(stream):
        """
        保证在`通用换行模式`下打开文件
        """
        for line in stream.splitlines():
            yield line

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', 'utf-8')
        serializer = parser_context["view"].get_serializer_class()()

        try:
            stream_data = stream.read()
            binary = self._universal_newlines(stream_data)
            rows = self._gen_rows(binary, charset=encoding)

            header = next(rows)
            fields_map = self._get_fields_map(serializer)
            header = [fields_map.get(name, '') for name in header]

            data = []
            for row in rows:
                row_data = dict(zip(header, row))
                row_data = {k: v for k, v in row_data.items() if k.strip() and v.strip()}
                data.append(row_data)
            return data

        except Exception as e:
            logger.debug(e, exc_info=True)
