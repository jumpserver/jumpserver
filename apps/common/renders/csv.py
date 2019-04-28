# ~*~ coding: utf-8 ~*~
#

import unicodecsv

from six import BytesIO
from rest_framework.renderers import BaseRenderer


class JMSCSVRender(BaseRenderer):

    media_type = 'text/csv'
    format = 'csv'
    serializer = None
    action = None

    def _get_labels(self):
        fields = self.serializer.get_fields()
        labels = {k: v.label for k, v in fields.items() if v.label}
        return labels

    def _get_header(self):
        fields = self.serializer.get_fields()
        if self.action == 'import':
            header = [k for k, v in fields.items() if not v.read_only]
        elif self.action == 'update':
            header = [k for k, v in fields.items() if not v.read_only]
            header.insert(0, 'id')
        else:
            header = [k for k, v in fields.items() if not v.write_only]
        return header

    @staticmethod
    def _gen_table(data, header, labels=None):
        labels = labels or {}
        yield [labels.get(k, k) for k in header]

        for item in data:
            row = [item.get(key) for key in header]
            yield row

    def render(self, data, media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        encoding = renderer_context.get('encoding', 'utf-8')
        self.serializer = renderer_context['view'].get_serializer_class()()
        self.action = renderer_context['request'].query_params.get('action', 'export')

        header = self._get_header()
        labels = self._get_labels()
        table = self._gen_table(data, header, labels)

        csv_buffer = BytesIO()
        csv_writer = unicodecsv.writer(csv_buffer, encoding=encoding)
        for row in table:
            csv_writer.writerow(row)

        return csv_buffer.getvalue()
