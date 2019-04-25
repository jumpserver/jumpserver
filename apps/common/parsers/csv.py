from django.conf import settings

from rest_framework.exceptions import ParseError, NotFound
from rest_framework_csv.orderedrows import OrderedRows
from rest_framework_csv.parsers import (
    CSVParser, unicode_csv_reader, universal_newlines
)


class JMSCSVParser(CSVParser):
    serializer = None

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
        self.serializer = serializer

        delimiter = parser_context.get('delimiter', ',')
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        try:
            strdata = stream.read()
            binary = universal_newlines(strdata)
            rows = unicode_csv_reader(binary, delimiter=delimiter, charset=encoding)
            data = OrderedRows(next(rows))
            for row in rows:
                row_data = dict(zip(data.header, row))
                row_data = self.row_data_pop_empty(row_data)
                data.append(row_data)
            if not data:
                msg = 'Please fill in the valid data to csv before import'
                raise NotFound(msg)
            trans_data = self.trans_data(data)
            return trans_data
        except Exception as exc:
            raise ParseError('CSV parse error - %s' % str(exc))

    def trans_data(self, data):
        new_data = []
        for entry in data:
            entry = self.filter_valid_data(entry)
            new_data.append(entry)
        return new_data

    def trans_entry(self, entry):
        new_entry = {}
        for k, v in entry.items():
            entry = {name: v for name, field in
                     self.serializer.get_fields().items() if k == field.label}
            new_entry.update(entry)
        return new_entry

    def filter_valid_data(self, entry):
        entry = self.trans_entry(entry)
        if entry:
            entry = {k: v for k, v in entry.items() if k in
                     getattr(self.serializer.Meta, "csv_fields", None)}
        if not entry:
            raise NotFound('Please upload the right template of CSV file！')
        return entry

    def row_data_pop_empty(self, row_data):
        data = {k: v for k, v in row_data.items() if v}
        return data