import pyexcel
from .base import BaseFileParser


class ExcelFileParser(BaseFileParser):

    media_type = 'text/xlsx'

    def generate_rows(self, stream_data):
        workbook = pyexcel.get_book(file_type='xlsx', file_content=stream_data)
        # 默认获取第一个工作表sheet
        sheet = workbook.sheet_by_index(0)
        rows = sheet.rows()
        return rows
