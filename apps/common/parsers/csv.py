from django.conf import settings

from rest_framework.exceptions import ParseError, NotFound
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
                row_data = self.row_data_pop_empty(row_data)
                data.append(row_data)
            if not data:
                raise NotFound('Please fill in the valid data to csv before import')
            return data
        except Exception as exc:
            raise ParseError('CSV parse error - %s' % str(exc))

    def row_data_pop_empty(self, row_data):
        new_row_data = dict()
        for k, v in row_data.items():
            if not v:
                continue
            new_row_data[k] = v
        return new_row_data