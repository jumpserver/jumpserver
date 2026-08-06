from .base import BaseService
from ..hands import *

__all__ = ['AIService']


class AIService(BaseService):
    def __init__(self, **kwargs):
        self.worker = kwargs.get('worker', 2)
        super().__init__(**kwargs)

    @property
    def cmd(self):
        print('\n- Start independent Chat AI ASGI Server')
        bind = f'{settings.CHAT_AI_BIND_HOST}:{settings.CHAT_AI_LISTEN_PORT}'
        return [
            'gunicorn', 'jumpserver.ai_asgi:application',
            '-b', bind,
            '-k', 'uvicorn.workers.UvicornWorker',
            '-w', str(self.worker),
            '--timeout', '600',
            '--graceful-timeout', '30',
            '--max-requests', '2048',
            '--max-requests-jitter', '256',
            '--access-logfile', '-',
        ]

    @property
    def cwd(self):
        return APPS_DIR

