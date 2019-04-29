# ~*~ coding: utf-8 ~*~
#

import unicodecsv

from six import BytesIO
from rest_framework.renderers import BaseRenderer

from ..utils import get_logger

logger = get_logger(__file__)


class JMSCSVRender(BaseRenderer):

    media_type = 'text/csv'
    format = 'csv'

    @staticmethod
    def _get_header(fields, action):
        if action == 'import':
            header = [k for k, v in fields.items() if not v.read_only and k != 'id']
        elif action == 'update':
            header = [k for k, v in fields.items() if not v.read_only]
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
        request = renderer_context['request']
        action = request.query_params.get('action', 'export')
        view = renderer_context['view']

        try:
            serializer = view.get_serializerd()
        except Exception as e:
            logger.debug(e, exc_info=True)
            value = 'The resource not support export!'.encode('utf-8')
        else:
            fields = serializer.get_fields()
            header = self._get_header(fields, action)
            labels = {k: v.label for k, v in fields.items() if v.label}
            table = self._gen_table(data, header, labels)

            csv_buffer = BytesIO()
            csv_writer = unicodecsv.writer(csv_buffer, encoding=encoding)
            for row in table:
                csv_writer.writerow(row)

            value = csv_buffer.getvalue()

        return value
