import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta


class DailyTimedRotatingFileHandler(TimedRotatingFileHandler):
    def rotator(self, source, dest):
        """ Override the original method to rotate the log file daily."""
        dest = self._get_rotate_dest_filename(source)
        if os.path.exists(source) and not os.path.exists(dest):
            # 存在多个服务进程时, 保证只有一个进程成功 rotate
            os.rename(source, dest)

    @staticmethod
    def _get_rotate_dest_filename(source):
        date_yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        path = [os.path.dirname(source), date_yesterday, os.path.basename(source)]
        filename = os.path.join(*path)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        return filename
