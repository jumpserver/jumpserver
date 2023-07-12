from common.utils import get_logger
from ..base import BaseVault

logger = get_logger(__name__)

__all__ = ['Vault']


class Vault(BaseVault):

    def is_active(self):
        return True, ''

    def _get(self, instance):
        secret = getattr(instance, '_secret', None)
        return secret

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

    def _clean_db_secret(self, instance):
        """ Ignore *重要* 不能删除本地 secret """
        pass
