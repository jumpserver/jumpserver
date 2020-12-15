import abc
from datetime import datetime
from rest_framework.renderers import BaseRenderer
from rest_framework.utils import encoders, json

from common.utils import get_logger

logger = get_logger(__file__)


class BaseFileRenderer(BaseRenderer):
    # 渲染模版标识, 导入、导出、更新模版: ['import', 'update', 'export']
    template = 'export'
    serializer = None

    @staticmethod
    def _check_validation_data(data):
        detail_key = "detail"
        if detail_key in data:
            return False
        return True

    @staticmethod
    def _json_format_response(response_data):
        return json.dumps(response_data)

    def set_response_disposition(self, response):
        serializer = self.serializer
        if response and hasattr(serializer, 'Meta') and hasattr(serializer.Meta, "model"):
            filename_prefix = serializer.Meta.model.__name__.lower()
        else:
            filename_prefix = 'download'
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = "{}_{}.{}".format(filename_prefix, now, self.format)
        disposition = 'attachment; filename="{}"'.format(filename)
        response['Content-Disposition'] = disposition

    def get_rendered_fields(self):
        fields = self.serializer.fields
        if self.template == 'import':
            return [v for k, v in fields.items() if not v.read_only and k != "org_id" and k != 'id']
        elif self.template == 'update':
            return [v for k, v in fields.items() if not v.read_only and k != "org_id"]
        else:
            return [v for k, v in fields.items() if not v.write_only and k != "org_id"]

    @staticmethod
    def get_column_titles(render_fields):
        return [
            '*{}'.format(field.label) if field.required else str(field.label)
            for field in render_fields
        ]

    def process_data(self, data):
        results = data['results'] if 'results' in data else data

        if isinstance(results, dict):
            results = [results]

        if self.template == 'import':
            results = [results[0]] if results else results

        else:
            # 限制数据数量
            results = results[:10000]
        # 会将一些 UUID 字段转化为 string
        results = json.loads(json.dumps(results, cls=encoders.JSONEncoder))
        return results

    @staticmethod
    def generate_rows(data, render_fields):
        for item in data:
            row = []
            for field in render_fields:
                value = item.get(field.field_name)
                value = str(value) if value else ''
                row.append(value)
            yield row

    @abc.abstractmethod
    def initial_writer(self):
        raise NotImplementedError

    def write_column_titles(self, column_titles):
        self.write_row(column_titles)

    def write_rows(self, rows):
        for row in rows:
            self.write_row(row)

    @abc.abstractmethod
    def write_row(self, row):
        raise NotImplementedError

    @abc.abstractmethod
    def get_rendered_value(self):
        raise NotImplementedError

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return bytes()

        if not self._check_validation_data(data):
            return self._json_format_response(data)

        try:
            renderer_context = renderer_context or {}
            request = renderer_context['request']
            response = renderer_context['response']
            view = renderer_context['view']
            self.template = request.query_params.get('template', 'export')
            self.serializer = view.get_serializer()
            self.set_response_disposition(response)
        except Exception as e:
            logger.debug(e, exc_info=True)
            value = 'The resource not support export!'.encode('utf-8')
            return value

        try:
            rendered_fields = self.get_rendered_fields()
            column_titles = self.get_column_titles(rendered_fields)
            data = self.process_data(data)
            rows = self.generate_rows(data, rendered_fields)
            self.initial_writer()
            self.write_column_titles(column_titles)
            self.write_rows(rows)
            value = self.get_rendered_value()
        except Exception as e:
            logger.debug(e, exc_info=True)
            value = 'Render error! ({})'.format(self.media_type).encode('utf-8')
            return value

        return value

