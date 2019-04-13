# -*- coding: utf-8 -*-
#
import csv
import codecs

from django.utils import timezone
from django.http import HttpResponse
from rest_framework.generics import ListCreateAPIView

from common.utils import get_logger

logger = get_logger(__file__)


class ExportExcelUtil:

    def __init__(self, filename, export_fields=None,
                 header=None, content=None):
        self.filename = filename
        self.export_fields = export_fields
        self.header = header
        self.content = content

    def get_excel_response(self):
        excel_response = HttpResponse(content_type='text/csv')
        excel_response[
            'Content-Disposition'] = 'attachment; filename="%s"' % self.filename
        excel_response.write(codecs.BOM_UTF8)
        return excel_response

    def write_content_to_excel(self):
        response = self.get_excel_response()
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)
        if not self.header:
            return response
        if self.header:
            writer.writerow(self.header)
        if self.content:
            for row in self.content:
                data = [row.get(field.name, '') for field in self.export_fields]
                writer.writerow(data)
        return response


class BaseExportAPIView(ListCreateAPIView):
    model = ''
    export_fields = ''
    csv_filename_prefix = ''

    def get_export_fields(self):
        """
        :return: Return the fields that need to be exported
        """
        if not self.export_fields:
            error = "%s should either include a export_fields attribute, or " \
                    "override the get_export_fields() method." % self.__class__.__name__
            logger.debug(error)
            return []
        if not self.model:
            error = "%s should either include a model attribute, or override " \
                    "the get_export_fields() method." % self.__class__.__name__
            logger.debug(error)
            return []

        export_fields = [field for field in self.model._meta.fields
                         if field.name in self.export_fields]

        return export_fields

    def get_export_header(self):
        """
        Write the excel header based on the exported field
        :return: Return the header of the first row field in excel
        """
        export_fields = self.get_export_fields()
        if not export_fields:
            return export_fields
        header = [field.name for field in export_fields]
        return header

    def get_export_content(self):
        """
        :return: Return the data to be exported
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return serializer.data

    def generate_filename(self):
        filename = '{}-{}.csv'.format(self.csv_filename_prefix,
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        return filename

    @staticmethod
    def get_excel_util(csv_filename_prefix, export_fields, header, content):
        excel_util = ExportExcelUtil(
            csv_filename_prefix, export_fields=export_fields,
            header=header, content=content
        )
        return excel_util

    def list(self, request, *args, **kwargs):
        filename = self.generate_filename()
        export_fields = self.get_export_fields()
        header = self.get_export_header()
        content = self.get_export_content()

        excel_utils = self.get_excel_util(filename, export_fields, header, content)
        excel_utils.write_content_to_excel()
        response = excel_utils.write_content_to_excel()
        return response
