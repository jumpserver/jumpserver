from celery import shared_task
from django.utils.translation import gettext, gettext_lazy as _

from common.utils import get_logger
from ops.celery.decorator import register_as_period_task
from ops.celery.task_logging import TaskLog
from orgs.utils import tmp_to_root_org, tmp_to_org

logger = get_logger(__name__)


@shared_task(verbose_name=_('Check credential rotation readiness'))
@register_as_period_task(interval=60)
def check_credential_readiness():
    with TaskLog(logger, gettext('Check credential rotation readiness')) as log:
        from accounts.credential_rotation.manager import CredentialRotationManager
        from accounts.models import ApplicationCredential
        with tmp_to_root_org():
            switched = list(ApplicationCredential.objects.filter(
                is_active=True, mode='alternating_rotation', status='waiting_switch',
            ).values_list('id', 'org_id'))
        for credential_id, org_id in switched:
            log.checked += 1
            try:
                with tmp_to_org(org_id):
                    credential, blockers = CredentialRotationManager(credential_id).check_usage()
                if blockers:
                    log.skip(gettext('Waiting for client confirmation or the source-account quiet period.'))
                else:
                    log.processed += 1
            except Exception:
                log.fail(gettext('Unable to check credential rotation readiness.'))
                logger.exception(gettext('Unable to check rotation readiness: credential=%(credential)s.'), {
                    'credential': credential_id,
                })
