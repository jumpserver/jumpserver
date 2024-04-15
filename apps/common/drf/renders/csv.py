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

    def write_row(self, row):
        row_escape = []
        for d in row:
            if isinstance(d, str) and d.strip().startswith(('=', '@')):
                d = "'{}".format(d)
                row_escape.append(d)
            else:
                row_escape.append(d)
        self.writer.writerow(row_escape)

    def get_rendered_value(self):
        value = self.buffer.getvalue()
        return value
