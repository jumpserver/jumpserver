from .celery_base import CeleryBaseService

__all__ = ['CeleryDefaultService']


class CeleryDefaultService(CeleryBaseService):

    def __init__(self,  **kwargs):
        queue = kwargs.pop('queue', 'celery')
        super().__init__(queue=queue, **kwargs)
