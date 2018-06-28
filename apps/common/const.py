# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _

create_success_msg = _("<b>%(name)s</b> was created successfully")
update_success_msg = _("<b>%(name)s</b> was updated successfully")
FILE_END_GUARD = ">>> Content End <<<"
celery_task_pre_key = "CELERY_"

tee_cache_key_fmt = "TEE_{}" 
tee_cache_expiration = 86400 
