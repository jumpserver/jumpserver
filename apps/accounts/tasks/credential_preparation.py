from celery import shared_task
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org, tmp_to_org


@shared_task(verbose_name=_('Check credential rotation preparation'))
@register_as_period_task(interval=60)
def check_credential_preparations():
    from accounts.credential_rotation.preparation import PHASES, notify_ready
    from accounts.models import ApplicationCredential
    with tmp_to_root_org():
        policies = list(ApplicationCredential.objects.filter(
            is_active=True, mode='alternating_rotation', status__in=PHASES,
        ).values_list('id', 'org_id'))
    for credential_id, org_id in policies:
        try:
            with tmp_to_org(org_id):
                notify_ready(credential_id)
        except Exception:
            get_logger(__name__).exception('Cannot check rotation preparation %s', credential_id)
