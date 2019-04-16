# -*- coding: utf-8 -*-
#

from django.utils import timezone
from rest_framework_csv import renderers
from rest_framework.generics import ListCreateAPIView

from common.utils import get_logger

logger = get_logger(__file__)


class BaseExportAPIView(ListCreateAPIView):
    model = ''
    csv_filename_prefix = ''
    renderer_classes = (renderers.CSVStreamingRenderer,)

    def generate_filename(self):
            filename = '{}-{}.csv'.format(self.csv_filename_prefix,
                timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
            )
            return filename

    def get_renderer_context(self):
        try:
            context = super().get_renderer_context()
            model_fields = self.model._meta.fields
            serializer_fields = self.get_serializer_class().Meta.fields
            fields =[field.name for field in model_fields] \
                if serializer_fields == '__all__' else serializer_fields

            context['header'] = fields
            context['labels'] = dict([
                (field.name, field.verbose_name) for field in model_fields
                if field.name in context['header']
            ])
            return context
        except AttributeError as e:
            error = "'%s' should either include a `model` attribute, "
            logger.error(error % self.__class__.__name__)
            return super().get_renderer_context()

    def list(self, request, *args, **kwargs):
        response = super().list(self, request, *args, **kwargs)
        response['Content-Disposition'] = \
            'attachment; filename="%s"' % self.generate_filename()
        return response