# ~*~ coding: utf-8 ~*~
#

import unicodecsv
import codecs
from datetime import datetime

from six import BytesIO
from rest_framework.renderers import BaseRenderer
from rest_framework.utils import encoders, json

from common.utils import get_logger

logger = get_logger(__file__)


class JMSCSVRender(BaseRenderer):

    media_type = 'text/csv'
    format = 'csv'

    @staticmethod
    def _get_show_fields(fields, template):
        if template in ('import', 'update'):
            return [v for k, v in fields.items() if not v.read_only and k != "org_id"]
        else:
            return [v for k, v in fields.items() if not v.write_only and k != "org_id"]

    @staticmethod
    def _gen_table(data, fields):
        yield ['*{}'.format(f.label) if f.required else f.label for f in fields]

        for item in data:
            row = [item.get(f.field_name) for f in fields]
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

        if isinstance(data, dict):
            data = data.get("results", [])

        if template == 'import':
            data = [data[0]] if data else data

        data = json.loads(json.dumps(data, cls=encoders.JSONEncoder))

        try:
            serializer = view.get_serializer()
            self.set_response_disposition(serializer, renderer_context)
        except Exception as e:
            logger.debug(e, exc_info=True)
            value = 'The resource not support export!'.encode('utf-8')
        else:
            fields = serializer.fields
            show_fields = self._get_show_fields(fields, template)
            table = self._gen_table(data, show_fields)

            csv_buffer = BytesIO()
            csv_buffer.write(codecs.BOM_UTF8)
            csv_writer = unicodecsv.writer(csv_buffer, encoding='utf-8')
            for row in table:
                csv_writer.writerow(row)

            value = csv_buffer.getvalue()

        return value
