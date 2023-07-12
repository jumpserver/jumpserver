from common.utils import get_logger
from ..base import BaseVault

logger = get_logger(__name__)

__all__ = ['LocalVault']


class LocalVault(BaseVault):

    def is_active(self, *args, **kwargs):
        return True

    def _get(self, instance):
        secret = getattr(instance, '_secret', '')
        data = {'secret': secret}
        return data

    def _create(self, instance):
        """ Ignore """
        pass

    def _update(self, instance):
        """ Ignore """
        pass

    def _delete(self, instance):
        """ Ignore """
        pass

    def _save_metadata(self, instance, metadata):
        """ Ignore """
        pass

    @staticmethod
    def _clean_db_secret(instance):
        """ *重要* 不能删除本地 secret """
        pass
