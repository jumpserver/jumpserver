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
        self.ws.row_dimensions[self.row_count].height = 20
        column_count = 0
        for cell_value in row:
            # 处理非法字符
            column_count += 1
            cell_value = ILLEGAL_CHARACTERS_RE.sub(r'', str(cell_value))
            self.ws.cell(row=self.row_count, column=column_count, value=str(cell_value))

    def after_render(self):
        for col in self.ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            adjusted_width = (max_length + 2) * 1.0
            adjusted_width = 300 if adjusted_width > 300 else adjusted_width
            adjusted_width = 30 if adjusted_width < 30 else adjusted_width
            self.ws.column_dimensions[column].width = adjusted_width
            self.wb.save('/tmp/test.xlsx')

    def get_rendered_value(self):
        value = save_virtual_workbook(self.wb)
        return value
