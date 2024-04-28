# ~*~ coding: utf-8 ~*~
#

import chardet
import unicodecsv

from common.utils import lazyproperty
from .base import BaseFileParser
from ..const import CSV_FILE_ESCAPE_CHARS


class CSVFileParser(BaseFileParser):
    media_type = 'text/csv'

    @lazyproperty
    def match_escape_chars(self):
        chars = []
        for c in CSV_FILE_ESCAPE_CHARS:
            dq_char = '"{}'.format(c)
            sg_char = "'{}".format(c)
            chars.append(dq_char)
            chars.append(sg_char)
        return tuple(chars)


    @staticmethod
    def _universal_newlines(stream):
        """
        保证在`通用换行模式`下打开文件
        """
        for line in stream.splitlines():
            yield line
    
    def __parse_row(self, row):
        row_escape = []
        for d in row:
            if isinstance(d, str) and d.strip().startswith(self.match_escape_chars):
                d = d.lstrip("'").lstrip('"')
            row_escape.append(d)
        return row_escape

    def generate_rows(self, stream_data):
        detect_result = chardet.detect(stream_data)
        encoding = detect_result.get("encoding", "utf-8")
        lines = self._universal_newlines(stream_data)
        csv_reader = unicodecsv.reader(lines, encoding=encoding)
        for row in csv_reader:
            row = self.__parse_row(row)
            yield row
