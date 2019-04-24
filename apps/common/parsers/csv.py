from django.conf import settings

from rest_framework.exceptions import ParseError
from rest_framework_csv.orderedrows import OrderedRows
from rest_framework_csv.parsers import (
    CSVParser, unicode_csv_reader, universal_newlines
)


class JMSCSVParser(CSVParser):
    def parse(self, stream, media_type=None, parser_context=None):
        if parser_context is None:
            parser_context = {}
        view = parser_context.get("view")
        if not view:
            return super().parse(stream, media_type=None,
                                 parser_context=parser_context)
        serializer = view.get_serializer()
        if not serializer:
            return super().parse(stream, media_type=None,
                                 parser_context=parser_context)
        csv_fields = getattr(serializer.Meta, "csv_fields", None)

        delimiter = parser_context.get('delimiter', ',')
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)

        try:
            strdata = stream.read()
            binary = universal_newlines(strdata)
            rows = unicode_csv_reader(binary, delimiter=delimiter, charset=encoding)
            data = OrderedRows(next(rows))
            for row in rows:
                row_data = dict(zip(csv_fields, row))
                data.append(row_data)
            return data
        except Exception as exc:
            raise ParseError('CSV parse error - %s' % str(exc))