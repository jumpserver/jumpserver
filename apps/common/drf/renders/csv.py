# ~*~ coding: utf-8 ~*~
#

import codecs
import unicodecsv
from six import BytesIO

from .base import BaseFileRenderer


class CSVFileRenderer(BaseFileRenderer):
    media_type = 'text/csv'
    format = 'csv'

    writer = None
    buffer = None

    def initial_writer(self):
        csv_buffer = BytesIO()
        csv_buffer.write(codecs.BOM_UTF8)
        csv_writer = unicodecsv.writer(csv_buffer, encoding='utf-8')
        self.buffer = csv_buffer
        self.writer = csv_writer

    def write_column_titles(self, column_titles):
        titles = [c['name'] for c in column_titles]
        self.write_row(titles)

    def write_row(self, row):
        self.writer.writerow(row)

    def get_rendered_value(self):
        value = self.buffer.getvalue()
        return value
