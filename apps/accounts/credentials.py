import re
import string
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import (
    AutomationTypes, ChangeSecretRecordStatusChoice,
    CredentialIssueStatus, CredentialLeaseStatus,
    CredentialPolicyMode, CredentialPolicyStatus,
    SecretStrategy, SecretType, Source,
)
from accounts.utils import SecretGenerator, validate_account_username
from assets.tasks.common import generate_automation_execution_data
from common.const import Status, Trigger
from common.utils import get_logger


logger = get_logger(__name__)


class CredentialError(Exception):
    def __init__(self, code, detail, status_code=400):
        self.code = code
        self.detail = str(detail)
        self.status_code = status_code
        super().__init__(self.detail)


class CredentialPolicyService:
    # ponytail: one asset per policy; make this configurable only when a real
    # platform proves that five minutes is insufficient.
    automation_timeout = 300
    recovery_grace = 60
    username_fields = {'application', 'policy', 'random', 'timestamp'}
    dynamic_method_pairs = {
        'push_account_posix': 'remove_account_posix',
        'push_account_local_windows': 'remove_account_windows',
        'push_account_ad_windows': 'remove_account_ad_windows',
        'push_account_mysql': 'remove_account_mysql',
        'push_account_postgresql': 'remove_account_postgresql',
        'push_account_mongodb': 'remove_account_mongodb',
        'push_account_oracle': 'remove_account_oracle',
        'push_account_sqlserver': 'remove_account_sqlserver',
    }
    username_max_lengths = {
        'push_account_posix': 32,
        'push_account_local_windows': 20,
        'push_account_ad_windows': 20,
        'push_account_mysql': 32,
        'push_account_postgresql': 63,
        'push_account_mongodb': 128,
        'push_account_oracle': 30,
        'push_account_sqlserver': 128,
    }

    @classmethod
    def validate_dynamic_automation(cls, asset, secret_type=None):
        automation = getattr(asset.platform, 'automation', None)
        push_method = getattr(automation, 'push_account_method', None)
        expected_remove = cls.dynamic_method_pairs.get(push_method)
        if (
            not automation
            or not automation.ansible_enabled
            or not automation.push_account_enabled
            or not automation.remove_account_enabled
            or not expected_remove
            or automation.remove_account_method != expected_remove
        ):
            raise CredentialError(
                'UNSUPPORTED_DYNAMIC_PLATFORM',
                _('The platform automation does not support safe temporary accounts'),
                409,
            )
        if secret_type == SecretType.SSH_KEY and push_method != 'push_account_posix':
            raise CredentialError(
                'UNSUPPORTED_DYNAMIC_SECRET_TYPE',
                _('The platform does not support temporary SSH key accounts'),
                409,
            )
        return automation

    @classmethod
    def validate_username_template(cls, template):
        fields = set()
        try:
            for __, field, spec, conversion in string.Formatter().parse(template):
                if field:
                    if spec or conversion:
                        raise ValueError
                    fields.add(field)
        except (TypeError, ValueError, KeyError):
            raise CredentialError(
                'INVALID_USERNAME_TEMPLATE',
                _('Invalid username template'),
            )
        unknown = fields - cls.username_fields
        if unknown:
            raise CredentialError(
                'INVALID_USERNAME_TEMPLATE',
                _('Unsupported username template variables: %(fields)s') % {
                    'fields': ', '.join(sorted(unknown)),
                },
            )
        if 'random' not in fields:
            raise CredentialError(
                'INVALID_USERNAME_TEMPLATE',
                _('Temporary account username template must contain {random}'),
            )
        return template

    @staticmethod
    def _username_part(value):
        return re.sub(r'[^A-Za-z0-9_.-]+', '_', str(value)).strip('_')

    @classmethod
    def render_username(cls, policy):
        cls.validate_username_template(policy.username_template)
        values = {
            'application': cls._username_part(policy.application.name),
            'policy': cls._username_part(policy.name),
            'random': uuid.uuid4().hex[:16],
            'timestamp': timezone.now().strftime('%Y%m%d%H%M%S'),
        }
        username = cls._username_part(
            policy.username_template.format(**values)
        )
        try:
            push_method = policy.asset.platform.automation.push_account_method
        except AttributeError:
            push_method = None
        if push_method == 'push_account_oracle':
            username = re.sub(r'[^A-Za-z0-9_$#]+', '_', username)
            if not username[:1].isalpha():
                username = f'J_{username}'
        max_length = cls.username_max_lengths.get(push_method, 128)
        if len(username) > max_length:
            random_suffix = values['random']
            prefix_length = max_length - len(random_suffix) - 1
            prefix = username[:prefix_length].rstrip('_.-')
            username = f'{prefix}_{random_suffix}'
        username = validate_account_username(username)
        if not username:
            raise CredentialError(
                'INVALID_USERNAME_TEMPLATE', _('Username cannot be empty'),
            )
        return username

    @staticmethod
    def _create_execution(task_name, automation_type, snapshot, trigger=Trigger.manual):
        from accounts.models import AutomationExecution

        data = generate_automation_execution_data(
            task_name, automation_type, snapshot,
        )
        while AutomationExecution.objects.filter(id=data['id']).exists():
            data['id'] = str(uuid.uuid4())
        return AutomationExecution.objects.create(
            type=automation_type, trigger=trigger, **data,
        )

    @staticmethod
    def _claim_pending_execution(execution):
        from celery import current_task
        from accounts.models import AutomationExecution

        with transaction.atomic():
            execution = AutomationExecution.objects.select_for_update().get(
                id=execution.id,
            )
            if execution.status != Status.pending:
                return execution, False
            snapshot = dict(execution.snapshot or {})
            request = getattr(current_task, 'request', None)
            task_id = getattr(request, 'id', None)
            worker_hostname = getattr(request, 'hostname', None)
            if task_id:
                snapshot['celery_task_id'] = str(task_id)
            if worker_hostname:
                snapshot['celery_worker_hostname'] = worker_hostname
            execution.snapshot = snapshot
            execution.status = Status.running
            execution.date_start = timezone.now()
            execution.save(update_fields=['snapshot', 'status', 'date_start'])
            return execution, True

    @classmethod
    def prepare_rotation(cls, policy, trigger=Trigger.manual):
        from accounts.models import CredentialPolicy

        with transaction.atomic():
            policy = CredentialPolicy.objects.select_for_update().get(
                id=policy.id,
            )
            if policy.mode != CredentialPolicyMode.static:
                raise CredentialError(
                    'INVALID_POLICY_MODE',
                    _('Only rotating account policies can be rotated'),
                    409,
                )
            allowed_statuses = (
                (CredentialPolicyStatus.enabled,)
                if trigger == Trigger.timing
                else (
                    CredentialPolicyStatus.enabled,
                    CredentialPolicyStatus.uncertain,
                    CredentialPolicyStatus.disabled,
                )
            )
            if policy.status not in allowed_statuses:
                return policy.last_execution, False

            account = policy.account
            previous_status = policy.status
            execution = cls._create_execution(
                _('Rotate application credential'),
                AutomationTypes.change_secret,
                {
                    'assets': [str(policy.asset_id)],
                    'accounts': [str(account.id)],
                    'secret_type': account.secret_type,
                    'secret_strategy': SecretStrategy.random,
                    'password_rules': policy.password_rules,
                    'params': policy.platform_params,
                    'check_conn_after_change': True,
                    'management_account': str(policy.management_account_id),
                    'credential_policy': str(policy.id),
                    'credential_policy_previous_status': previous_status,
                    'credential_policy_previous_error': policy.last_error,
                    'deadline': (
                        timezone.now().timestamp() + cls.automation_timeout
                    ),
                },
                trigger=trigger,
            )
            policy.status = CredentialPolicyStatus.rotating
            policy.last_execution = execution
            policy.date_last_run = timezone.now()
            policy.last_error = ''
            policy.save(update_fields=[
                'status', 'last_execution', 'date_last_run', 'last_error',
            ])
            return execution, True

    @classmethod
    def execute_rotation(cls, policy, execution):
        execution.start()
        cls.finalize_rotation(policy.id, execution.id)
        return execution

    @classmethod
    def rotate(cls, policy, trigger=Trigger.manual):
        execution, created = cls.prepare_rotation(policy, trigger)
        if created:
            execution, claimed = cls._claim_pending_execution(execution)
            if claimed:
                cls.execute_rotation(policy, execution)
        return execution

    @classmethod
    def finalize_rotation(cls, policy_id, execution_id):
        from accounts.models import (
            ChangeSecretRecord, CredentialPolicy,
            CredentialPolicyVersion,
        )

        with transaction.atomic():
            policy = CredentialPolicy.objects.select_for_update().get(
                id=policy_id,
            )
            if policy.last_execution_id != execution_id:
                return policy
            record = ChangeSecretRecord.objects.filter(
                execution_id=execution_id,
                account_id=policy.account_id,
            ).order_by('-date_created').first()
            previous_status = (policy.last_execution.snapshot or {}).get(
                'credential_policy_previous_status',
                CredentialPolicyStatus.enabled,
            )
            preserve_disabled = policy.status in (
                CredentialPolicyStatus.disabled,
                CredentialPolicyStatus.disabling,
            ) or previous_status == CredentialPolicyStatus.disabled
            disabled_status = (
                CredentialPolicyStatus.disabling
                if policy.status == CredentialPolicyStatus.disabling
                else CredentialPolicyStatus.disabled
            )

            if record and record.status == ChangeSecretRecordStatusChoice.success:
                policy.account.refresh_from_db()
                published = CredentialPolicyVersion.objects.filter(
                    policy=policy,
                    change_secret_record=record,
                ).first()
                if published:
                    version = published.version
                else:
                    version = policy.current_version + 1
                    CredentialPolicyVersion.objects.create(
                        policy=policy,
                        version=version,
                        account=policy.account,
                        account_version=policy.account.version,
                        change_secret_record=record,
                        org_id=policy.org_id,
                    )
                policy.current_version = max(policy.current_version, version)
                policy.date_last_rotated = timezone.now()
                policy.last_error = ''
                policy.status = (
                    disabled_status
                    if preserve_disabled
                    else CredentialPolicyStatus.enabled
                )
            elif not record or record.status in (
                ChangeSecretRecordStatusChoice.pending,
                ChangeSecretRecordStatusChoice.unverified,
            ):
                policy.last_error = (
                    record.error if record else str(_('Rotation result is unknown'))
                )
                policy.status = (
                    disabled_status
                    if preserve_disabled
                    else CredentialPolicyStatus.uncertain
                )
            else:
                policy.last_error = record.error or str(_('Credential rotation failed'))
                if preserve_disabled:
                    policy.status = disabled_status
                elif previous_status == CredentialPolicyStatus.uncertain:
                    policy.status = CredentialPolicyStatus.uncertain
                else:
                    policy.status = CredentialPolicyStatus.enabled

            policy.save(update_fields=[
                'status', 'current_version', 'date_last_rotated', 'last_error',
            ])
            return policy

    @classmethod
    def create_issue_request(
            cls, policy, idempotency_key=None, remote_addr=None,
            timeout=30,
    ):
        from accounts.models import (
            CredentialIssueRequest, CredentialLease, CredentialPolicy,
        )

        with transaction.atomic():
            policy = CredentialPolicy.objects.select_for_update().get(id=policy.id)
            if policy.mode != CredentialPolicyMode.dynamic:
                raise CredentialError(
                    'INVALID_POLICY_MODE',
                    _('Only temporary account policies can issue credentials'),
                    409,
                )
            if policy.status != CredentialPolicyStatus.enabled:
                raise CredentialError(
                    'CREDENTIAL_POLICY_DISABLED',
                    _('Credential policy is not enabled'), 403,
                )
            cls.validate_dynamic_automation(
                policy.asset, policy.account_template.secret_type,
            )
            if not policy.asset.all_valid_accounts.filter(
                id=policy.management_account_id,
            ).exists():
                raise CredentialError(
                    'MANAGEMENT_ACCOUNT_UNAVAILABLE',
                    _('Management account is not available'), 409,
                )

            if idempotency_key:
                existing = CredentialIssueRequest.objects.filter(
                    policy=policy, idempotency_key=idempotency_key,
                ).first()
                if existing:
                    return existing, False

            occupied = CredentialLease.objects.filter(
                policy=policy,
                status__in=[
                    CredentialLeaseStatus.active,
                    CredentialLeaseStatus.revoking,
                ],
            ).count()
            occupied += CredentialIssueRequest.objects.filter(
                policy=policy,
                status__in=[
                    CredentialIssueStatus.pending,
                    CredentialIssueStatus.running,
                    CredentialIssueStatus.cleaning,
                ],
            ).count()
            if occupied >= policy.max_active_leases:
                raise CredentialError(
                    'LEASE_QUOTA_EXCEEDED',
                    _('Maximum active leases reached'), 409,
                )

            issue = CredentialIssueRequest.objects.create(
                policy=policy,
                idempotency_key=idempotency_key or None,
                deadline=timezone.now() + timedelta(seconds=timeout),
                remote_addr=remote_addr,
                org_id=policy.org_id,
            )
            return issue, True

    @classmethod
    def issue(cls, issue):
        from accounts.models import (
            Account, CredentialIssueRequest, CredentialLease,
            CredentialPolicy, PushSecretRecord,
        )

        with transaction.atomic():
            issue = CredentialIssueRequest.objects.select_for_update().get(
                id=issue.id,
            )
            if issue.status != CredentialIssueStatus.pending:
                return issue
            if issue.deadline <= timezone.now():
                cls._fail_issue(
                    issue, CredentialIssueStatus.timed_out,
                    'CREDENTIAL_ISSUE_TIMEOUT', _('Credential issue timed out'),
                )
                return issue

            policy = issue.policy
            username = cls.render_username(policy)
            template = policy.account_template
            secret = SecretGenerator(
                SecretStrategy.random,
                template.secret_type,
                policy.password_rules or template.password_rules,
            ).get_secret()
            issue.username = username
            issue.provisional_secret = secret
            issue.status = CredentialIssueStatus.running
            transient_account_id = uuid.uuid4()
            execution = cls._create_execution(
                _('Issue temporary credential'),
                AutomationTypes.credential_issue,
                {
                    'assets': [str(policy.asset_id)],
                    'accounts': [str(transient_account_id)],
                    'secret_type': policy.account_template.secret_type,
                    'params': policy.platform_params,
                    'check_conn_after_change': True,
                    'management_account': str(policy.management_account_id),
                    'issue_request': str(issue.id),
                    'require_absent': True,
                    'deadline': issue.deadline.timestamp(),
                },
            )
            issue.execution = execution
            issue.save(update_fields=[
                'username', 'provisional_secret', 'status', 'execution',
            ])

        execution.start()

        record = PushSecretRecord.objects.filter(
            execution=execution,
        ).order_by('-date_created').first()
        issue.refresh_from_db()
        if record and 'JMS_CREDENTIAL_ACCOUNT_EXISTS' in (record.error or ''):
            cls._fail_issue(
                issue,
                CredentialIssueStatus.failed,
                'ACCOUNT_ALREADY_EXISTS',
                _('Temporary account username already exists'),
            )
            return issue
        if issue.status in (
            CredentialIssueStatus.failed,
            CredentialIssueStatus.timed_out,
        ):
            return issue
        if issue.status != CredentialIssueStatus.running:
            return cls.cleanup_issue(
                issue,
                status=(
                    CredentialIssueStatus.timed_out
                    if issue.error_code == 'CREDENTIAL_ISSUE_TIMEOUT'
                    else CredentialIssueStatus.failed
                ),
                code=issue.error_code or 'CREDENTIAL_ISSUE_CANCELED',
                error=issue.error or _('Credential issue was canceled'),
            )
        if issue.deadline <= timezone.now():
            return cls.cleanup_issue(
                issue, status=CredentialIssueStatus.timed_out,
            )
        if not record or record.status != ChangeSecretRecordStatusChoice.success:
            return cls.cleanup_issue(
                issue,
                status=CredentialIssueStatus.failed,
                code='CREDENTIAL_ISSUE_FAILED',
                error=(record.error if record else _('Credential issue failed')),
            )

        CredentialIssueRequest.objects.filter(
            id=issue.id,
            status=CredentialIssueStatus.running,
        ).update(vault_cleanup_pending=True)
        try:
            with transaction.atomic():
                issue = CredentialIssueRequest.objects.select_for_update().get(
                    id=issue.id,
                )
                policy = CredentialPolicy.objects.select_for_update().get(
                    id=issue.policy_id,
                )
                if (
                    issue.status != CredentialIssueStatus.running
                    or issue.deadline <= timezone.now()
                    or policy.status != CredentialPolicyStatus.enabled
                ):
                    raise CredentialError(
                        'CREDENTIAL_ISSUE_CANCELED',
                        _('Credential issue was canceled'), 409,
                    )

                now = timezone.now()
                lease = CredentialLease.objects.create(
                    policy=policy,
                    username=issue.username,
                    date_expires=now + timedelta(seconds=policy.default_ttl),
                    date_max_expires=now + timedelta(seconds=policy.max_ttl),
                    issue_execution=execution,
                    org_id=policy.org_id,
                )
                template = issue.policy.account_template
                account = Account(
                    id=execution.snapshot['accounts'][0],
                    name=issue.username,
                    username=issue.username,
                    secret=issue.provisional_secret,
                    secret_type=template.secret_type,
                    privileged=False,
                    is_active=True,
                    asset=issue.policy.asset,
                    su_from=template.get_su_from_account(issue.policy.asset),
                    source=Source.CREDENTIAL_LEASE,
                    source_id=str(lease.id),
                    org_id=policy.org_id,
                )
                account.save()
                lease.account = account
                lease.save(update_fields=['account'])
                issue.lease = lease
                issue.status = CredentialIssueStatus.succeeded
                issue.provisional_secret = None
                issue.replay_until = now + timedelta(minutes=5)
                issue.date_completed = now
                issue.error_code = ''
                issue.error = ''
                issue.vault_cleanup_pending = False
                issue.save(update_fields=[
                    'lease', 'status', 'provisional_secret', 'replay_until',
                    'date_completed', 'error_code', 'error',
                    'vault_cleanup_pending',
                ])
                return issue
        except (CredentialError, IntegrityError) as error:
            return cls.cleanup_issue(
                issue,
                status=CredentialIssueStatus.failed,
                code=(
                    error.code if isinstance(error, CredentialError)
                    else 'ACCOUNT_ALREADY_EXISTS'
                ),
                error=str(error),
            )
        except Exception:
            logger.exception('Publish temporary credential failed: %s', issue.id)
            return cls.cleanup_issue(
                issue,
                status=CredentialIssueStatus.failed,
                code='CREDENTIAL_PUBLISH_FAILED',
                error=_('Credential was created remotely but could not be published'),
            )

    @staticmethod
    def _fail_issue(issue, status, code, error):
        issue.status = status
        issue.provisional_secret = None
        issue.error_code = code
        issue.error = str(error)
        issue.date_completed = timezone.now()
        issue.save(update_fields=[
            'status', 'provisional_secret', 'error_code', 'error',
            'date_completed', 'vault_cleanup_pending',
        ])

    @staticmethod
    def _cleanup_issue_vault_account(issue):
        from accounts.backends import vault_client
        from accounts.models import Account

        account_id = issue.execution.snapshot['accounts'][0]
        account = Account.objects.filter(id=account_id).first()
        if account:
            CredentialPolicyService._delete_local_account(account)
            return
        account = Account(
            id=account_id,
            asset_id=issue.policy.asset_id,
            org_id=issue.org_id,
        )
        vault_client.delete(account, force=True)

    @classmethod
    def _prepare_remote_removal(
            cls, policy, username, platform_params=None,
            management_account_id=None,
    ):
        return cls._create_execution(
            _('Revoke temporary credential'),
            AutomationTypes.remove_account,
            {
                'assets': [str(policy.asset_id)],
                'accounts': [{
                    'asset': str(policy.asset_id),
                    'username': username,
                }],
                'delete': 'remote',
                'params': (
                    policy.platform_params
                    if platform_params is None else platform_params
                ),
                'management_account': str(
                    management_account_id or policy.management_account_id
                ),
                'deadline': (
                    timezone.now().timestamp() + cls.automation_timeout
                ),
            },
        )

    @classmethod
    def _remove_remote(
            cls, policy, username, platform_params=None,
            management_account_id=None,
    ):
        execution = cls._prepare_remote_removal(
            policy, username, platform_params, management_account_id,
        )
        execution.start()
        return execution

    @classmethod
    def cleanup_issue(
            cls, issue, status=CredentialIssueStatus.timed_out,
            code='CREDENTIAL_ISSUE_TIMEOUT', error=None,
    ):
        from accounts.models import CredentialIssueRequest, PushSecretRecord

        with transaction.atomic():
            issue = CredentialIssueRequest.objects.select_for_update().get(
                id=issue.id,
            )
            if issue.status in (
                CredentialIssueStatus.succeeded,
                CredentialIssueStatus.failed,
                CredentialIssueStatus.timed_out,
            ):
                return issue
            if issue.execution_id and PushSecretRecord.objects.filter(
                execution_id=issue.execution_id,
                error__contains='JMS_CREDENTIAL_ACCOUNT_EXISTS',
            ).exists():
                cls._fail_issue(
                    issue,
                    CredentialIssueStatus.failed,
                    'ACCOUNT_ALREADY_EXISTS',
                    _('Temporary account username already exists'),
                )
                return issue
            if issue.execution_id and not issue.execution.date_finished:
                issue.status = CredentialIssueStatus.cleaning
                issue.error_code = code
                issue.error = str(error or _('Credential issue timed out'))
                issue.save(update_fields=['status', 'error_code', 'error'])
                return issue
            cleanup_execution = issue.cleanup_execution
            if (
                cleanup_execution
                and not cleanup_execution.date_finished
                and cleanup_execution.status != Status.pending
            ):
                return issue
            issue.provisional_secret = None
            if issue.username and not cleanup_execution:
                snapshot = issue.execution.snapshot if issue.execution_id else {}
                cleanup_execution = cls._prepare_remote_removal(
                    issue.policy,
                    issue.username,
                    snapshot.get('params'),
                    snapshot.get('management_account'),
                )
                issue.cleanup_execution = cleanup_execution
            issue.status = CredentialIssueStatus.cleaning
            issue.error_code = code
            issue.error = str(error or issue.error or _('Credential issue timed out'))
            issue.save(update_fields=[
                'status', 'provisional_secret', 'error_code', 'error',
                'cleanup_execution',
            ])

        cleanup_should_start = False
        if cleanup_execution and not cleanup_execution.date_finished:
            cleanup_execution, cleanup_should_start = (
                cls._claim_pending_execution(cleanup_execution)
            )
            if not cleanup_should_start:
                return issue

        cleanup_error = ''
        if cleanup_execution:
            try:
                if cleanup_should_start:
                    cleanup_execution.start()
                if cleanup_execution.status != Status.success:
                    cleanup_error = str(_('Remote account cleanup failed'))
            except Exception as exc:
                cleanup_error = str(exc)

        vault_error = ''
        if issue.vault_cleanup_pending:
            try:
                cls._cleanup_issue_vault_account(issue)
            except Exception as exc:
                logger.exception(
                    'Delete rolled back temporary credential from vault failed: %s',
                    issue.id,
                )
                vault_error = str(exc)

        detail = '; '.join(filter(None, [
            str(error) if error else '', cleanup_error, vault_error,
        ])) or str(_('Credential issue timed out'))
        with transaction.atomic():
            issue = CredentialIssueRequest.objects.select_for_update().get(
                id=issue.id,
            )
            if issue.status in (
                CredentialIssueStatus.succeeded,
                CredentialIssueStatus.failed,
                CredentialIssueStatus.timed_out,
            ):
                return issue
            if vault_error:
                issue.error = detail
                issue.save(update_fields=['error'])
                return issue
            issue.vault_cleanup_pending = False
            cls._fail_issue(issue, status, code, detail)
            return issue

    @classmethod
    def renew(cls, lease, increment=None):
        from accounts.models import CredentialLease

        with transaction.atomic():
            lease = CredentialLease.objects.select_for_update().get(
                id=lease.id,
            )
            now = timezone.now()
            if lease.policy.status != CredentialPolicyStatus.enabled:
                raise CredentialError(
                    'CREDENTIAL_POLICY_DISABLED',
                    _('Credential policy is not enabled'), 403,
                )
            if (
                lease.status != CredentialLeaseStatus.active
                or lease.date_expires <= now
            ):
                raise CredentialError(
                    'LEASE_NOT_ACTIVE', _('Credential lease is not active'), 409,
                )
            if lease.date_expires >= lease.date_max_expires:
                raise CredentialError(
                    'LEASE_NOT_RENEWABLE',
                    _('Credential lease reached its maximum lifetime'), 409,
                )
            seconds = (
                lease.policy.default_ttl
                if increment is None else increment
            )
            if not isinstance(seconds, int) or seconds <= 0:
                raise CredentialError(
                    'INVALID_INCREMENT', _('Renew increment must be positive'),
                )
            remaining = (
                lease.date_max_expires - lease.date_expires
            ).total_seconds()
            lease.date_expires = (
                lease.date_max_expires
                if seconds >= remaining
                else lease.date_expires + timedelta(seconds=seconds)
            )
            lease.date_last_renewed = now
            lease.renew_count += 1
            lease.save(update_fields=[
                'date_expires', 'date_last_renewed', 'renew_count',
            ])
            return lease

    @staticmethod
    def _delete_local_account(account):
        from accounts.backends import vault_client

        account_id = account.id
        history_model = account.history.model
        historical_accounts = list(history_model.objects.filter(id=account_id))

        def delete_from_vault(instance):
            vault_client.delete(instance, force=True)

        for historical in historical_accounts:
            delete_from_vault(historical)
        delete_from_vault(account)

        for historical in historical_accounts:
            historical.skip_vault_when_deleting = True
            historical.delete()
        account.skip_vault_when_deleting = True
        account.delete()

    @classmethod
    def revoke(cls, lease, reason='manual'):
        from accounts.models import CredentialLease

        with transaction.atomic():
            lease = CredentialLease.objects.select_for_update().get(
                id=lease.id,
            )
            if lease.status in (
                CredentialLeaseStatus.revoked,
                CredentialLeaseStatus.expired,
            ):
                return lease
            if lease.revoke_execution_id:
                if (
                    not lease.revoke_execution.date_finished
                    and lease.revoke_execution.status != Status.pending
                ):
                    return lease
                execution = lease.revoke_execution
            else:
                snapshot = (
                    lease.issue_execution.snapshot
                    if lease.issue_execution_id else {}
                )
                execution = cls._prepare_remote_removal(
                    lease.policy,
                    lease.username,
                    snapshot.get('params'),
                    snapshot.get('management_account'),
                )
            lease.status = CredentialLeaseStatus.revoking
            lease.revoke_reason = lease.revoke_reason or reason
            lease.revoke_execution = execution
            lease.save(update_fields=[
                'status', 'revoke_reason', 'revoke_execution',
            ])

        revoke_should_start = False
        if not execution.date_finished:
            execution, revoke_should_start = cls._claim_pending_execution(
                execution,
            )
            if not revoke_should_start:
                return lease

        error = ''
        try:
            if revoke_should_start:
                execution.start()
            succeeded = execution.status == Status.success
            if not succeeded:
                error = str(_('Remote account revocation failed'))
        except Exception as exc:
            succeeded = False
            error = str(exc)

        local_deleted = True
        try:
            if lease.account:
                cls._delete_local_account(lease.account)
        except Exception as exc:
            local_deleted = False
            logger.exception(
                'Delete local temporary credential failed: %s', lease.id,
            )
            error = '; '.join(filter(None, [error, str(exc)]))

        with transaction.atomic():
            lease = CredentialLease.objects.select_for_update().get(
                id=lease.id,
            )
            if lease.status in (
                CredentialLeaseStatus.revoked,
                CredentialLeaseStatus.expired,
            ):
                return lease
            if not local_deleted:
                lease.status = CredentialLeaseStatus.revoking
                lease.revoke_succeeded = False
                lease.revoke_error = error
                lease.save(update_fields=[
                    'status', 'revoke_succeeded', 'revoke_error',
                ])
                return lease
            lease.status = (
                CredentialLeaseStatus.expired
                if lease.revoke_reason == 'expired'
                else CredentialLeaseStatus.revoked
            )
            lease.date_revoked = timezone.now()
            lease.revoke_succeeded = succeeded and not error
            lease.revoke_error = error
            lease.revoke_execution = execution
            lease.save(update_fields=[
                'status', 'date_revoked', 'revoke_succeeded',
                'revoke_error', 'revoke_execution',
            ])
            return lease
