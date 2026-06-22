import os

from .celery_base import CeleryBaseService

__all__ = ['CeleryAnsibleService']


class CeleryAnsibleService(CeleryBaseService):

    def __init__(self, **kwargs):
        kwargs['queue'] = os.environ.get('CELERY_ANSIBLE_QUEUE', 'ansible')
        super().__init__(**kwargs)
