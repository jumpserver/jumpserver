from common.utils import get_logger
from ..base.vault import BaseVault
from ...const import VaultTypeChoices

logger = get_logger(__name__)

__all__ = ['Vault']


class Vault(BaseVault):
    type = VaultTypeChoices.local

    def is_active(self):
        return True, ''

    def _get(self, entry):
        secret = getattr(entry.instance, '_secret', None)
        return secret

    def _create(self, entry):
        """ Ignore """
        pass

    def _update(self, entry):
        """ Ignore """
        pass

    def _delete(self, entry):
        """ Ignore """
        pass

    def _save_metadata(self, entry, metadata):
        """ Ignore """
        pass

    def _clean_db_secret(self, instance):
        """ Ignore *重要* 不能删除本地 secret """
        pass
