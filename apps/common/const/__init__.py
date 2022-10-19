# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _

create_success_msg = _("%(name)s was created successfully")
update_success_msg = _("%(name)s was updated successfully")
FILE_END_GUARD = ">>> Content End <<<"
celery_task_pre_key = "CELERY_"
KEY_CACHE_RESOURCE_IDS = "RESOURCE_IDS_{}"

# AD User AccountDisable
# https://docs.microsoft.com/en-us/troubleshoot/windows-server/identity/useraccountcontrol-manipulate-account-properties
LDAP_AD_ACCOUNT_DISABLE = 2
