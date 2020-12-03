from openpyxl import Workbook
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
            column_count += 1
            self.ws.cell(row=self.row_count, column=column_count, value=cell_value)

    def get_rendered_value(self):
        value = save_virtual_workbook(self.wb)
        return value
