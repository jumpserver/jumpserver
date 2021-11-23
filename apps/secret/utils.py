# -*- coding: utf-8 -*-
#
from common.utils import get_logger

logger = get_logger(__name__)


def instance_read_and_replace_data(instance):
    secret_data = instance.vault.read_secret(instance.pk)
    for k, v in secret_data.items():
        setattr(instance, k, v)


