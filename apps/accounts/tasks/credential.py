from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import (
    CredentialIssueStatus, CredentialLeaseStatus,
    CredentialPolicyMode, CredentialPolicyStatus,
)
from accounts.credentials import CredentialPolicyService
from common.const import Status, Trigger
from common.utils import get_logger
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_org, tmp_to_root_org

logger = get_logger(__name__)

__all__ = [
    'rotate_credential_policy_task', 'issue_credential_task',
    'cleanup_credential_issue_task', 'revoke_credential_lease_task',
    'disable_credential_policy_task', 'reconcile_credential_policies_task',
]


def _credential_execution_is_overdue(execution, overdue_before):
    try:
        deadline = float((execution.snapshot or {}).get('deadline'))
    except (TypeError, ValueError):
        return False
    return deadline <= overdue_before


def _recover_overdue_credential_executions(now):
    from accounts.automations.recovery import finalize_interrupted_execution
    from accounts.models import (
        AutomationExecution, CredentialIssueRequest, CredentialLease,
        CredentialPolicy,
    )

    with tmp_to_root_org():
        execution_ids = set(CredentialPolicy.objects.filter(
            mode=CredentialPolicyMode.static,
            status__in=[
                CredentialPolicyStatus.rotating,
                CredentialPolicyStatus.disabling,
            ],
            last_execution__isnull=False,
        ).values_list('last_execution_id', flat=True))
        execution_ids.update(CredentialIssueRequest.objects.filter(
            status__in=[
                CredentialIssueStatus.pending,
                CredentialIssueStatus.running,
                CredentialIssueStatus.cleaning,
            ],
            execution__isnull=False,
        ).values_list('execution_id', flat=True))
        execution_ids.update(CredentialIssueRequest.objects.filter(
            status=CredentialIssueStatus.cleaning,
            cleanup_execution__isnull=False,
        ).values_list('cleanup_execution_id', flat=True))
        execution_ids.update(CredentialLease.objects.filter(
            status=CredentialLeaseStatus.revoking,
            revoke_execution__isnull=False,
        ).values_list('revoke_execution_id', flat=True))
        executions = list(AutomationExecution.objects.filter(
            id__in=execution_ids,
            status__in=[Status.pending, Status.running],
        ).only('id', 'snapshot'))

    overdue_before = now.timestamp() - CredentialPolicyService.recovery_grace
    overdue_ids = [
        execution.id for execution in executions
        if _credential_execution_is_overdue(execution, overdue_before)
    ]

    recovered = 0
    reason = (
        'Credential automation exceeded its hard deadline; the remote '
        'credential state may be unknown.'
    )
    for execution_id in overdue_ids:
        try:
            recovered += bool(finalize_interrupted_execution(
                execution_id, reason, status=Status.canceled,
            ))
        except Exception:
            logger.exception(
                'Recover overdue credential execution failed: %s',
                execution_id,
            )
    return recovered


@shared_task(
    queue='ansible', priority=9,
    verbose_name=_('Rotate application credential'),
)
def rotate_credential_policy_task(
        policy_id, trigger='manual', execution_id=None,
):
    from accounts.models import AutomationExecution, CredentialPolicy

    with tmp_to_root_org():
        policy = CredentialPolicy.objects.filter(id=policy_id).first()
    if not policy:
        return {'status': 'not_found'}
    with tmp_to_org(policy.org_id):
        if execution_id:
            with transaction.atomic():
                policy = CredentialPolicy.objects.select_for_update().get(
                    id=policy.id,
                )
                execution = AutomationExecution.objects.select_for_update().filter(
                    id=execution_id,
                ).first()
                if (
                    not execution
                    or policy.last_execution_id != execution.id
                    or policy.status != CredentialPolicyStatus.rotating
                    or execution.status != Status.pending
                ):
                    return {'status': 'skipped'}
                execution, claimed = (
                    CredentialPolicyService._claim_pending_execution(
                        execution,
                    )
                )
                if not claimed:
                    return {'status': 'skipped'}
            CredentialPolicyService.execute_rotation(policy, execution)
        else:
            execution = CredentialPolicyService.rotate(
                policy,
                trigger=(
                    Trigger.timing if trigger == 'timing' else Trigger.manual
                ),
            )
    return {
        'status': getattr(execution, 'status', 'skipped'),
        'execution_id': str(execution.id) if execution else None,
    }


@shared_task(
    queue='ansible', priority=5,
    verbose_name=_('Issue temporary credential'),
)
def issue_credential_task(issue_id):
    from accounts.models import CredentialIssueRequest

    with tmp_to_root_org():
        issue = CredentialIssueRequest.objects.filter(id=issue_id).first()
    if not issue:
        return {'status': 'not_found'}
    with tmp_to_org(issue.org_id):
        try:
            issue = CredentialPolicyService.issue(issue)
        except Exception:
            logger.exception('Issue temporary credential failed: %s', issue.id)
            issue = CredentialPolicyService.cleanup_issue(
                issue,
                status=CredentialIssueStatus.failed,
                code='CREDENTIAL_ISSUE_FAILED',
                error=_('Credential issue failed'),
            )
    return {'status': issue.status, 'request_id': str(issue.id)}


@shared_task(
    queue='ansible', priority=0,
    verbose_name=_('Clean timed out credential issue'),
)
def cleanup_credential_issue_task(issue_id):
    from accounts.models import CredentialIssueRequest

    with tmp_to_root_org():
        issue = CredentialIssueRequest.objects.filter(id=issue_id).first()
    if not issue:
        return {'status': 'not_found'}
    with tmp_to_org(issue.org_id):
        code = issue.error_code or 'CREDENTIAL_ISSUE_TIMEOUT'
        issue = CredentialPolicyService.cleanup_issue(
            issue,
            status=(
                CredentialIssueStatus.timed_out
                if code == 'CREDENTIAL_ISSUE_TIMEOUT'
                else CredentialIssueStatus.failed
            ),
            code=code,
            error=issue.error or None,
        )
    return {'status': issue.status, 'request_id': str(issue.id)}


@shared_task(
    queue='ansible', priority=0,
    verbose_name=_('Revoke temporary credential'),
)
def revoke_credential_lease_task(lease_id, reason='manual'):
    from accounts.models import CredentialLease

    with tmp_to_root_org():
        lease = CredentialLease.objects.filter(id=lease_id).first()
    if not lease:
        return {'status': 'not_found'}
    with tmp_to_org(lease.org_id):
        lease = CredentialPolicyService.revoke(lease, reason=reason)
    return {'status': lease.status, 'lease_id': str(lease.id)}


@shared_task(
    queue='ansible', priority=0,
    verbose_name=_('Disable credential policy'),
)
def disable_credential_policy_task(policy_id):
    from accounts.models import (
        CredentialIssueRequest, CredentialLease, CredentialPolicy,
    )

    with tmp_to_root_org():
        policy = CredentialPolicy.objects.filter(id=policy_id).first()
    if not policy:
        return {'status': 'not_found'}

    with tmp_to_org(policy.org_id):
        policy.refresh_from_db(fields=['status'])
        if policy.status != CredentialPolicyStatus.disabling:
            return {'status': 'skipped', 'policy_id': str(policy.id)}
        if policy.mode == CredentialPolicyMode.static:
            execution = policy.last_execution
            if execution and not execution.date_finished:
                return {
                    'status': CredentialPolicyStatus.disabling,
                    'policy_id': str(policy.id),
                }
            if execution:
                CredentialPolicyService.finalize_rotation(
                    policy.id, execution.id,
                )
            cleanup_pending = False
        else:
            issues = list(CredentialIssueRequest.objects.filter(
                policy=policy,
                status__in=[
                    CredentialIssueStatus.pending,
                    CredentialIssueStatus.running,
                    CredentialIssueStatus.cleaning,
                ],
            ))
            for issue in issues:
                CredentialPolicyService.cleanup_issue(
                    issue,
                    status=CredentialIssueStatus.failed,
                    code='CREDENTIAL_POLICY_DISABLED',
                    error=_('Credential policy was disabled'),
                )

            leases = list(CredentialLease.objects.filter(
                policy=policy,
                status__in=[
                    CredentialLeaseStatus.active,
                    CredentialLeaseStatus.revoking,
                ],
            ))
            for lease in leases:
                CredentialPolicyService.revoke(
                    lease, reason='policy_disabled',
                )

            cleanup_pending = (
                CredentialIssueRequest.objects.filter(
                    policy=policy,
                    status__in=[
                        CredentialIssueStatus.pending,
                        CredentialIssueStatus.running,
                        CredentialIssueStatus.cleaning,
                    ],
                ).exists()
                or CredentialLease.objects.filter(
                    policy=policy,
                    status__in=[
                        CredentialLeaseStatus.active,
                        CredentialLeaseStatus.revoking,
                    ],
                ).exists()
                or CredentialLease.objects.filter(
                    policy=policy, account__isnull=False,
                ).exists()
            )
        if cleanup_pending:
            return {
                'status': CredentialPolicyStatus.disabling,
                'policy_id': str(policy.id),
            }

        with transaction.atomic():
            policy = CredentialPolicy.objects.select_for_update().get(
                id=policy.id,
            )
            if policy.status == CredentialPolicyStatus.disabling:
                policy.status = CredentialPolicyStatus.disabled
                policy.save(update_fields=['status'])
    return {'status': policy.status, 'policy_id': str(policy.id)}


@shared_task(
    verbose_name=_('Reconcile application credentials'),
)
@register_as_period_task(interval=60)
def reconcile_credential_policies_task():
    from accounts.models import (
        AutomationExecution, CredentialIssueRequest, CredentialLease,
        CredentialPolicy,
    )

    now = timezone.now()
    recovered_executions = _recover_overdue_credential_executions(now)
    with tmp_to_root_org():
        with transaction.atomic():
            leases = CredentialLease.objects.select_for_update().filter(
                status=CredentialLeaseStatus.active,
                date_expires__lte=now,
            )
            leases.update(
                status=CredentialLeaseStatus.revoking,
                revoke_reason='expired',
            )
        leases_to_revoke = list(CredentialLease.objects.filter(
            status=CredentialLeaseStatus.revoking,
        ).filter(
            Q(revoke_execution__isnull=True)
            | Q(revoke_execution__status=Status.pending)
            | Q(revoke_execution__date_finished__isnull=False)
        ).values_list('id', 'revoke_reason'))

        stale_issue_ids = []
        with transaction.atomic():
            finished_execution_ids = AutomationExecution.objects.filter(
                date_finished__isnull=False,
            ).values('id')
            issues = CredentialIssueRequest.objects.select_for_update().filter(
                Q(status__in=[
                    CredentialIssueStatus.pending,
                    CredentialIssueStatus.running,
                ]) | Q(
                    status=CredentialIssueStatus.cleaning,
                    execution__isnull=True,
                ) | Q(
                    status=CredentialIssueStatus.cleaning,
                    execution_id__in=finished_execution_ids,
                ),
                deadline__lte=now,
            )
            stale_issue_ids = list(issues.values_list('id', flat=True))
            issues.update(status=CredentialIssueStatus.cleaning)

        rotating = list(CredentialPolicy.objects.filter(
            status=CredentialPolicyStatus.rotating,
            last_execution__date_finished__isnull=False,
        ).values_list('id', 'last_execution_id', 'org_id'))
        disabling = list(CredentialPolicy.objects.filter(
            status=CredentialPolicyStatus.disabling,
        ).values_list('id', flat=True))

    for lease_id, reason in leases_to_revoke:
        revoke_credential_lease_task.apply_async(
            args=[str(lease_id)], kwargs={'reason': reason or 'manual'},
            priority=2 if reason == 'expired' else 0,
        )
    for issue_id in stale_issue_ids:
        cleanup_credential_issue_task.apply_async(
            args=[str(issue_id)], priority=0,
        )
    for policy_id, execution_id, org_id in rotating:
        with tmp_to_org(org_id):
            try:
                CredentialPolicyService.finalize_rotation(
                    policy_id, execution_id,
                )
            except Exception:
                logger.exception(
                    'Reconcile credential policy failed: %s', policy_id,
                )
    for policy_id in disabling:
        result = disable_credential_policy_task.apply_async(
            args=[str(policy_id)], priority=0,
        )
        with tmp_to_root_org():
            CredentialPolicy.objects.filter(id=policy_id).update(
                operation_task_id=result.id,
            )

    return {
        'recovered_executions': recovered_executions,
        'leases_to_revoke': len(leases_to_revoke),
        'stale_issues': len(stale_issue_ids),
        'rotations': len(rotating),
        'disabling': len(disabling),
    }
