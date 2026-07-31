from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts.const import (
    ApplicationAgentEventStatus, ApplicationAgentEventType, ApplicationAgentStatus,
    ApplicationSwitchItemStatus, ApplicationSwitchStatus,
)
from orgs.mixins.models import JMSOrgBaseModel

from .account import Account
from .application import IntegrationApplication


ACTIVE_SWITCH_STATUSES = (
    ApplicationSwitchStatus.RUNNING,
    ApplicationSwitchStatus.WAITING_CONFIRMATION,
    ApplicationSwitchStatus.ROLLING_BACK,
)


class IntegrationApplicationAgent(JMSOrgBaseModel):
    application = models.OneToOneField(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='agent', verbose_name=_('Application')
    )
    hostname = models.CharField(max_length=255, blank=True, verbose_name=_('Hostname'))
    platform = models.CharField(max_length=64, blank=True, verbose_name=_('Platform'))
    version = models.CharField(max_length=64, blank=True, verbose_name=_('Version'))
    date_last_used = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date last used')
    )
    error = models.TextField(blank=True, verbose_name=_('Error'))

    class Meta:
        verbose_name = _('Integration application Agent')

    @property
    def status(self):
        if self.error:
            return ApplicationAgentStatus.ERROR
        if (
            not self.date_last_used or
            self.date_last_used < timezone.now() - timedelta(seconds=90)
        ):
            return ApplicationAgentStatus.OFFLINE
        return ApplicationAgentStatus.ONLINE

    def touch(self, error=None):
        now = timezone.now()
        updates = {'date_last_used': now, 'date_updated': now}
        if error is not None:
            updates['error'] = error
            self.error = error
        IntegrationApplicationAgent.objects.filter(pk=self.pk).update(**updates)
        IntegrationApplication.objects.filter(pk=self.application_id).update(
            date_last_used=now, date_updated=now
        )
        self.date_last_used = now
        self.date_updated = now
        return self


class ApplicationAccountBinding(JMSOrgBaseModel):
    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='account_bindings', verbose_name=_('Application')
    )
    # Do not silently remove a credential still used by an application.
    current_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='application_bindings', verbose_name=_('Current account')
    )

    class Meta:
        unique_together = [('application', 'current_account')]
        ordering = ['application__name', 'current_account__name']
        verbose_name = _('Application account binding')

    @classmethod
    def sync_application(cls, application):
        accounts = application.accounts.value or {}
        account_ids = accounts.get('ids', []) if accounts.get('type') == 'ids' else []
        account_ids = set(Account.objects.filter(
            id__in=account_ids
        ).values_list('id', flat=True))
        application.account_bindings.exclude(
            current_account_id__in=account_ids
        ).delete()
        cls.objects.bulk_create([
            cls(
                org_id=application.org_id,
                application=application,
                current_account_id=account_id,
            )
            for account_id in account_ids
        ], ignore_conflicts=True)

    def move_to(self, account):
        application = IntegrationApplication.objects.select_for_update().get(
            pk=self.application_id
        )
        binding = ApplicationAccountBinding.objects.get(pk=self.pk)
        if binding.current_account_id == account.pk:
            return binding
        if ApplicationAccountBinding.objects.filter(
            application_id=binding.application_id, current_account=account
        ).exclude(pk=binding.pk).exists():
            raise ValidationError(_(
                'The target account is already bound to this application.'
            ))
        accounts = dict(application.accounts.value or {})
        account_ids = list(accounts.get('ids') or [])
        source_id = str(binding.current_account_id)
        target_id = str(account.pk)
        if source_id not in account_ids:
            raise ValidationError(_(
                'The application account binding is out of sync.'
            ))
        accounts['ids'] = [
            target_id if account_id == source_id else account_id
            for account_id in account_ids
        ]
        application.accounts = accounts
        application.save(update_fields=['accounts', 'date_updated'])
        binding.current_account = account
        binding.save(update_fields=['current_account', 'date_updated'])
        return binding


class ApplicationAccountSwitch(JMSOrgBaseModel):
    source_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='application_switches_as_source', verbose_name=_('Source account')
    )
    target_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='application_switches_as_target', verbose_name=_('Target account')
    )
    status = models.CharField(
        max_length=32, choices=ApplicationSwitchStatus.choices,
        default=ApplicationSwitchStatus.RUNNING, verbose_name=_('Status')
    )
    date_finished = models.DateTimeField(null=True, blank=True, verbose_name=_('Date finished'))

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('Application account switch')

    @classmethod
    def start(cls, source_account, target_account, user, comment=''):
        cls._validate_accounts(source_account, target_account)
        bindings = list(
            cls.get_affected_bindings(source_account).select_for_update().select_related(
                'application'
            )
        )
        cls._validate_bindings(bindings, target_account)
        switch = cls.objects.create(
            org_id=source_account.org_id,
            source_account=source_account,
            target_account=target_account,
            created_by=str(user),
            comment=comment,
        )
        switch._create_items(bindings)
        return switch

    @staticmethod
    def get_affected_bindings(account):
        return ApplicationAccountBinding.objects.filter(
            current_account=account,
            application__agent__isnull=False,
            application__is_active=True,
            org_id=account.org_id,
        )

    @classmethod
    def _validate_accounts(cls, source_account, target_account):
        if source_account.pk == target_account.pk:
            raise ValidationError({
                'target_account': _('Target account must differ from source account.')
            })
        if source_account.asset_id != target_account.asset_id:
            raise ValidationError({
                'target_account': _('Target account must belong to the same asset.')
            })

    @staticmethod
    def _validate_bindings(bindings, target_account):
        if not bindings:
            raise ValidationError({
                'source_account': _(
                    'This account is not used by any registered application Agent.'
                )
            })

        binding_ids = [binding.id for binding in bindings]
        if ApplicationAccountSwitchItem.objects.filter(
            binding_id__in=binding_ids,
            switch__status__in=ACTIVE_SWITCH_STATUSES,
        ).exists():
            raise ValidationError({
                'source_account': _('This account already has an active switch task.')
            })

        application_ids = [binding.application_id for binding in bindings]
        if ApplicationAccountBinding.objects.filter(
            application_id__in=application_ids,
            current_account=target_account,
        ).exists():
            raise ValidationError({
                'target_account': _(
                    'The target account is already bound to an affected application.'
                )
            })

    def _create_items(self, bindings):
        for binding in bindings:
            item = self.items.create(
                org_id=self.org_id,
                binding=binding,
            )
            item.events.create(
                org_id=self.org_id,
                event_type=ApplicationAgentEventType.SWITCH,
                desired_account=self.target_account,
            )

    def refresh_status(self):
        statuses = set(self.items.values_list('status', flat=True))
        if self.status == ApplicationSwitchStatus.ROLLING_BACK:
            if statuses and statuses <= {ApplicationSwitchItemStatus.ROLLED_BACK}:
                self._finish(ApplicationSwitchStatus.ROLLED_BACK)
        elif statuses and statuses <= {ApplicationSwitchItemStatus.CONFIRMED}:
            self._finish(ApplicationSwitchStatus.COMPLETED)
        elif statuses and statuses <= {
            ApplicationSwitchItemStatus.DELIVERED,
            ApplicationSwitchItemStatus.CONFIRMED,
        }:
            self.status = ApplicationSwitchStatus.WAITING_CONFIRMATION
            self.save(update_fields=['status', 'date_updated'])
        return self

    def _finish(self, status):
        self.status = status
        self.date_finished = timezone.now()
        self.save(update_fields=[
            'status', 'updated_by', 'date_finished', 'date_updated'
        ])

    def rollback(self, user):
        switch = self._lock_active(_('Only an active switch task can be rolled back.'))
        switch.status = ApplicationSwitchStatus.ROLLING_BACK
        switch.updated_by = str(user)
        switch.save(update_fields=['status', 'updated_by', 'date_updated'])
        switch._cancel_pending_events()
        for item in switch.items.select_related('binding__application'):
            item.prepare_rollback()
        return switch

    def end(self, user):
        switch = self._lock_active(_('The switch task is already finished.'))
        switch.updated_by = str(user)
        switch._finish(ApplicationSwitchStatus.ENDED)
        switch._cancel_pending_events()
        return switch

    def _lock_active(self, message):
        switch = ApplicationAccountSwitch.objects.select_for_update().get(pk=self.pk)
        if switch.status not in ACTIVE_SWITCH_STATUSES:
            raise ValidationError(message)
        return switch

    def _cancel_pending_events(self):
        IntegrationApplicationAgentEvent.objects.filter(
            item__switch=self, status=ApplicationAgentEventStatus.PENDING
        ).update(
            status=ApplicationAgentEventStatus.DELIVERED,
            date_delivered=timezone.now(),
        )


class ApplicationAccountSwitchItem(JMSOrgBaseModel):
    switch = models.ForeignKey(
        'accounts.ApplicationAccountSwitch', on_delete=models.CASCADE,
        related_name='items', verbose_name=_('Account switch')
    )
    binding = models.ForeignKey(
        'accounts.ApplicationAccountBinding', on_delete=models.PROTECT,
        related_name='switch_items', verbose_name=_('Application account binding')
    )
    status = models.CharField(
        max_length=32, choices=ApplicationSwitchItemStatus.choices,
        default=ApplicationSwitchItemStatus.PENDING, verbose_name=_('Status')
    )
    error = models.TextField(blank=True, verbose_name=_('Error'))
    date_delivered = models.DateTimeField(null=True, blank=True, verbose_name=_('Date delivered'))
    date_confirmed = models.DateTimeField(null=True, blank=True, verbose_name=_('Date confirmed'))

    class Meta:
        unique_together = [('switch', 'binding')]
        ordering = ['binding__application__name']
        verbose_name = _('Application account switch item')

    @property
    def application(self):
        return self.binding.application

    def confirm(self, user):
        switch = ApplicationAccountSwitch.objects.select_for_update().get(pk=self.switch_id)
        item = ApplicationAccountSwitchItem.objects.get(pk=self.pk)
        item.switch = switch
        status, account = item._confirmation_result()
        item.binding.move_to(account)
        item.status = status
        item.date_confirmed = timezone.now()
        item.updated_by = str(user)
        item.save(update_fields=['status', 'date_confirmed', 'updated_by', 'date_updated'])
        return item.switch.refresh_status()

    def _confirmation_result(self):
        if self.status == ApplicationSwitchItemStatus.DELIVERED:
            return ApplicationSwitchItemStatus.CONFIRMED, self.switch.target_account
        if self.status == ApplicationSwitchItemStatus.ROLLBACK_DELIVERED:
            return ApplicationSwitchItemStatus.ROLLED_BACK, self.switch.source_account
        raise ValidationError(_('The credential has not been delivered and cannot be confirmed.'))

    def prepare_rollback(self):
        self.status = ApplicationSwitchItemStatus.ROLLBACK_PENDING
        self.error = ''
        self.save(update_fields=['status', 'error', 'date_updated'])
        self.events.create(
            org_id=self.switch.org_id,
            event_type=ApplicationAgentEventType.ROLLBACK,
            desired_account=self.switch.source_account,
        )


class IntegrationApplicationAgentEvent(JMSOrgBaseModel):
    item = models.ForeignKey(
        'accounts.ApplicationAccountSwitchItem', on_delete=models.CASCADE,
        related_name='events', verbose_name=_('Account switch item')
    )
    event_type = models.CharField(
        max_length=16, choices=ApplicationAgentEventType.choices,
        verbose_name=_('Event type')
    )
    desired_account = models.ForeignKey(
        'accounts.Account', null=True, on_delete=models.SET_NULL,
        related_name='application_agent_events', verbose_name=_('Desired account')
    )
    status = models.CharField(
        max_length=16, choices=ApplicationAgentEventStatus.choices,
        default=ApplicationAgentEventStatus.PENDING, verbose_name=_('Status')
    )
    attempts = models.PositiveIntegerField(default=0, verbose_name=_('Attempts'))
    error = models.TextField(blank=True, verbose_name=_('Error'))
    date_delivered = models.DateTimeField(null=True, blank=True, verbose_name=_('Date delivered'))

    class Meta:
        ordering = ['date_created']
        verbose_name = _('Integration application Agent event')

    def report(self, success, error=''):
        switch = ApplicationAccountSwitch.objects.select_for_update().get(
            pk=self.item.switch_id
        )
        event = IntegrationApplicationAgentEvent.objects.select_related(
            'item__binding__application', 'item'
        ).get(pk=self.pk)
        event.item.switch = switch
        if event.status == ApplicationAgentEventStatus.DELIVERED:
            return event, True
        event._apply_report(success, error)
        switch.refresh_status()
        return event, False

    def _apply_report(self, success, error):
        now = timezone.now()
        self.attempts += 1
        self.error = error
        if success:
            self.status = ApplicationAgentEventStatus.DELIVERED
            self.date_delivered = now
            self.item.status = self.delivered_item_status
            self.item.error = ''
            self.item.date_delivered = now
        else:
            self.item.status = ApplicationSwitchItemStatus.FAILED
            self.item.error = error
        self.save(update_fields=['status', 'attempts', 'error', 'date_delivered', 'date_updated'])
        self.item.save(update_fields=['status', 'error', 'date_delivered', 'date_updated'])
        self.item.binding.application.agent.touch(error='' if success else error)

    @property
    def application(self):
        return self.item.binding.application

    @property
    def delivered_item_status(self):
        if self.event_type == ApplicationAgentEventType.ROLLBACK:
            return ApplicationSwitchItemStatus.ROLLBACK_DELIVERED
        return ApplicationSwitchItemStatus.DELIVERED

    def as_payload(self):
        return {
            'id': str(self.id),
            'type': self.event_type,
            'switch_id': str(self.item.switch_id),
            'item_id': str(self.item_id),
            'credential_id': str(self.item.binding_id),
            'desired_account_id': str(self.desired_account_id),
        }
