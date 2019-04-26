from django.conf import settings

from rest_framework.exceptions import ParseError, NotFound
from rest_framework_csv.orderedrows import OrderedRows
from rest_framework_csv.parsers import (
    CSVParser, unicode_csv_reader, universal_newlines
)


class JMSCSVParser(CSVParser):
    serializer = None

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        self.serializer = parser_context['view'].get_serializer()
        delimiter = parser_context.get('delimiter', ',')
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)

        try:
            strdata = stream.read()
            binary = universal_newlines(strdata)
            rows = unicode_csv_reader(binary, delimiter=delimiter, charset=encoding)
            data = OrderedRows(next(rows))
            header = self.trans_header_to_field_name(data.header)
            for row in rows:
                row_data = dict(zip(header, row))
                row_data = self.row_data_pop_empty(row_data)
                data.append(row_data)
            if not data:
                msg = 'Please fill in the valid data to csv before import'
                raise NotFound(msg)
            return data
        except Exception as exc:
            raise ParseError('CSV parse error - %s' % str(exc))

    def trans_header_to_field_name(self, header):
        fields = self.serializer.get_fields()
        csv_fields = getattr(self.serializer.Meta, "csv_fields", None)
        field_name_list = []

        for ele in header:
            field_name = [name for name, field in fields.items()
                          if ele == field.label]
            if not field_name and ele not in csv_fields:
                raise ParseError('[%s]是无效字段，请上传有效的csv文件' % ele)
            if field_name:
                field_name_list.append(field_name[0])
            else:
                field_name_list.append(ele)
        return field_name_list

    def row_data_pop_empty(self, row_data):
        data = {k: v for k, v in row_data.items() if v}
        return data