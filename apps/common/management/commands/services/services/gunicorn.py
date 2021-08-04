from ..hands import *
from .base import BaseService

__all__ = ['GunicornService']


class GunicornService(BaseService):

    def __init__(self):
        super().__init__(name='gunicorn')

    @property
    def cmd(self):
        print("\n- Start Gunicorn WSGI HTTP Server")

        log_format = '%(h)s %(t)s %(L)ss "%(r)s" %(s)s %(b)s '
        bind = f'{HTTP_HOST}:{HTTP_PORT}'
        cmd = [
            'gunicorn', 'jumpserver.wsgi',
            '-b', bind,
            '-k', 'gthread',
            '--threads', '10',
            '-w', str(WORKERS),
            '--max-requests', '4096',
            '--access-logformat', log_format,
            '--access-logfile', '-'
        ]
        if DEBUG:
            cmd.append('--reload')
        return cmd

    @property
    def cwd(self):
        return APPS_DIR
