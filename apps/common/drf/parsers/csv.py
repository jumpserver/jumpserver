# ~*~ coding: utf-8 ~*~
#

import chardet
import unicodecsv

from .base import BaseFileParser


class CSVFileParser(BaseFileParser):

    media_type = 'text/csv'

    @staticmethod
    def _universal_newlines(stream):
        """
        保证在`通用换行模式`下打开文件
        """
        for line in stream.splitlines():
            yield line

    def generate_rows(self, stream_data):
        detect_result = chardet.detect(stream_data)
        encoding = detect_result.get("encoding", "utf-8")
        lines = self._universal_newlines(stream_data)
        csv_reader = unicodecsv.reader(lines, encoding=encoding)
        for row in csv_reader:
            yield row
