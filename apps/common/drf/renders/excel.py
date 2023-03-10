from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.writer.excel import save_virtual_workbook

from .base import BaseFileRenderer


class ExcelFileRenderer(BaseFileRenderer):
    media_type = "application/xlsx"
    format = "xlsx"

    wb = None
    ws = None
    row_count = 0

    def initial_writer(self):
        self.wb = Workbook()
        self.ws = self.wb.active

    def write_row(self, row):
        self.row_count += 1
        column_count = 0
        for cell_value in row:
            # 处理非法字符
            column_count += 1
            cell_value = ILLEGAL_CHARACTERS_RE.sub(r'', str(cell_value))
            self.ws.cell(row=self.row_count, column=column_count, value=str(cell_value))

    def get_rendered_value(self):
        value = save_virtual_workbook(self.wb)
        return value
