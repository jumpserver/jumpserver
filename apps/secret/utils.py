# -*- coding: utf-8 -*-
#
from secret.backends.vault import vault_client
from secret.backends.vault import KVEngineVault
from common.utils import get_logger

logger = get_logger(__name__)


def is_model_setting_vault_field_and_active(model):
    if not hasattr(model, 'VAULT_FIELD') or not hasattr(model, 'VAULT_FIELD'):
        return False
    elif hasattr(model, 'secret'):
        return getattr(getattr(getattr(model, 'secret'), 'client'), 'is_active')
    else:
        return True


def instance_read_and_replace_data(instance):
    secret_data = instance.vault.read_secret(instance.pk)
    for k, v in secret_data.items():
        setattr(instance, k, v)


def init_vault_path():
    vault_models = []
    if vault_client.is_active:
        for model in vault_models:
            if not is_model_setting_vault_field_and_active(model):
                logger.error('{} not specified VAULT_FIELD'.format(model))
            else:
                model_name = model._meta.db_table
                model.vault = KVEngineVault(vault_client, model_name)
