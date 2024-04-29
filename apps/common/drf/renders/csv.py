# ~*~ coding: utf-8 ~*~
#

import codecs
import unicodecsv
from six import BytesIO

from .base import BaseFileRenderer
from ..const import CSV_FILE_ESCAPE_CHARS

class CSVFileRenderer(BaseFileRenderer):

    media_type = 'text/csv'
    format = 'csv'

    writer = None
    buffer = None

    escape_chars = tuple(CSV_FILE_ESCAPE_CHARS)

    def initial_writer(self):
        csv_buffer = BytesIO()
        csv_buffer.write(codecs.BOM_UTF8)
        csv_writer = unicodecsv.writer(csv_buffer, encoding='utf-8')
        self.buffer = csv_buffer
        self.writer = csv_writer
    
    def __render_row(self, row):
        row_escape = []
        for d in row:
            if isinstance(d, str) and d.strip().startswith(self.escape_chars):
                d = "'{}".format(d)
            row_escape.append(d)
        return row_escape

    def write_row(self, row):
        row = self.__render_row(row)
        self.writer.writerow(row)

    def get_rendered_value(self):
        value = self.buffer.getvalue()
        return value
