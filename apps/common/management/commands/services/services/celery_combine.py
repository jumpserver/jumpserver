from .celery_default import CeleryDefaultService

__all__ = ['CeleryCombineService']


class CeleryCombineService(CeleryDefaultService):

    def __init__(self, **kwargs):
        kwargs['queue'] = 'ansible,celery,cloud_sync'
        super().__init__(**kwargs)

