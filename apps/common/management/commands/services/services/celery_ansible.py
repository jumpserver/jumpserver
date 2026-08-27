from .celery_base import CeleryBaseService

__all__ = ['CeleryAnsibleService']


class CeleryAnsibleService(CeleryBaseService):

    def __init__(self, **kwargs):
        kwargs['queue'] = 'ansible'
        super().__init__(**kwargs)

    @property
    def cmd(self):
        return [*super().cmd, '--prefetch-multiplier', '1']
