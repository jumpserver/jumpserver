# ~*~ coding: utf-8 ~*~
#

import unicodecsv
import codecs
from datetime import datetime

from six import BytesIO
from rest_framework.renderers import BaseRenderer
from rest_framework.utils import encoders, json

from ..utils import get_logger

logger = get_logger(__file__)


class JMSCSVRender(BaseRenderer):

    media_type = 'text/csv'
    format = 'csv'

    @staticmethod
    def _get_header(fields, template):
        if template == 'import':
            header = [
                k for k, v in fields.items()
                if not v.read_only and k != 'org_id'
            ]
        elif template == 'update':
            header = [k for k, v in fields.items() if not v.read_only]
        else:
            # template in ['export']
            header = [k for k, v in fields.items() if not v.write_only]
        return header

    @staticmethod
    def _gen_table(data, header, labels=None):
        labels = labels or {}
        yield [labels.get(k, k) for k in header]

        for item in data:
            row = [item.get(key) for key in header]
            yield row

    def set_response_disposition(self, serializer, context):
        response = context.get('response')
        if response and hasattr(serializer, 'Meta') and \
                hasattr(serializer.Meta, "model"):
            model_name = serializer.Meta.model.__name__.lower()
            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = "{}_{}.csv".format(model_name, now)
            disposition = 'attachment; filename="{}"'.format(filename)
            response['Content-Disposition'] = disposition

    def render(self, data, media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        request = renderer_context['request']
        template = request.query_params.get('template', 'export')
        view = renderer_context['view']
        data = json.loads(json.dumps(data, cls=encoders.JSONEncoder))
        if template == 'import':
            data = [data[0]] if data else data

        try:
            serializer = view.get_serializer()
            self.set_response_disposition(serializer, renderer_context)
        except Exception as e:
            logger.debug(e, exc_info=True)
            value = 'The resource not support export!'.encode('utf-8')
        else:
            fields = serializer.get_fields()
            header = self._get_header(fields, template)
            labels = {k: v.label for k, v in fields.items() if v.label}
            table = self._gen_table(data, header, labels)

            csv_buffer = BytesIO()
            csv_buffer.write(codecs.BOM_UTF8)
            csv_writer = unicodecsv.writer(csv_buffer, encoding='utf-8')
            for row in table:
                csv_writer.writerow(row)

            value = csv_buffer.getvalue()

        return value
