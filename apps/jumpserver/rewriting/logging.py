import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path


class DailyDirectoryTimedRotatingFileHandler(TimedRotatingFileHandler):

    def __init__(self, filename, **kwargs):
        self._raw_filename = filename
        dated_filename = self._build_dated_filename()
        super().__init__(dated_filename, **kwargs)

    def doRollover(self):
        self.baseFilename = self._build_dated_filename()
        return super().doRollover()

    def _build_dated_filename(self):
        """ Custom: construct the filename with current date """
        date = datetime.now().strftime('%Y-%m-%d')
        raw_filepath = Path(self._raw_filename)
        filename = raw_filepath.parent / date / raw_filepath.name
        os.makedirs(filename.parent, exist_ok=True)
        return str(filename)
