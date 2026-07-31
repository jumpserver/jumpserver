from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts.const import (
    ApplicationAgentEventStatus, ApplicationAgentEventType, ApplicationAgentStatus,
    ApplicationSwitchItemStatus, ApplicationSwitchStatus,
)
from common.const.signals import OP_LOG_SKIP_SIGNAL
from orgs.mixins.models import JMSOrgBaseModel


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
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name=_('Last seen'))
    error = models.TextField(blank=True, verbose_name=_('Error'))

    class Meta:
        verbose_name = _('Integration application Agent')

    @property
    def status(self):
        if self.error:
            return ApplicationAgentStatus.ERROR
        if not self.last_seen or self.last_seen < timezone.now() - timedelta(seconds=90):
            return ApplicationAgentStatus.OFFLINE
        return ApplicationAgentStatus.ONLINE

    @transaction.atomic
    def touch(self, error=None):
        application = self.application.__class__.objects.select_for_update().get(
            pk=self.application_id
        )
        agent = self.__class__.objects.select_for_update().get(pk=self.pk)
        agent.last_seen = timezone.now()
        fields = ['last_seen', 'date_updated']
        if error is not None:
            agent.error = error
            fields.append('error')
        application.date_last_used = agent.last_seen
        setattr(application, OP_LOG_SKIP_SIGNAL, True)
        application.save(update_fields=['date_last_used', 'date_updated'])
        setattr(agent, OP_LOG_SKIP_SIGNAL, True)
        agent.save(update_fields=fields)
        return agent


class ApplicationAccountBinding(JMSOrgBaseModel):
    application = models.ForeignKey(
        'accounts.IntegrationApplication', on_delete=models.CASCADE,
        related_name='account_bindings', verbose_name=_('Application')
    )
    current_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='application_bindings', verbose_name=_('Current account')
    )

    class Meta:
        unique_together = [('application', 'current_account')]
        ordering = ['application__name', 'current_account__name']
        verbose_name = _('Application account binding')

    @transaction.atomic
    def move_to(self, account):
        binding = self.__class__.objects.select_for_update().get(pk=self.pk)
        if binding.current_account_id == account.pk:
            return binding
        if self.__class__.objects.filter(
            application_id=binding.application_id, current_account=account
        ).exclude(pk=binding.pk).exists():
            raise ValidationError(_(
                'The target account is already bound to this application.'
            ))

        application_model = self._meta.get_field('application').remote_field.model
        application = application_model.objects.select_for_update().get(
            pk=binding.application_id
        )
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
        application.accounts.set(accounts)
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
    @transaction.atomic
    def start(cls, source_account, target_account, user, comment=''):
        source_account = source_account.__class__.objects.select_for_update().get(
            pk=source_account.pk
        )
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

    @transaction.atomic
    def rollback(self, user):
        switch = self._lock_active(_('Only an active switch task can be rolled back.'))
        switch.status = ApplicationSwitchStatus.ROLLING_BACK
        switch.updated_by = str(user)
        switch.save(update_fields=['status', 'updated_by', 'date_updated'])
        switch._cancel_pending_events()
        for item in switch.items.select_related('binding__application'):
            item.prepare_rollback()
        return switch

    @transaction.atomic
    def end(self, user):
        switch = self._lock_active(_('The switch task is already finished.'))
        switch.updated_by = str(user)
        switch._finish(ApplicationSwitchStatus.ENDED)
        switch._cancel_pending_events()
        return switch

    def _lock_active(self, message):
        switch = self.__class__.objects.select_for_update().get(pk=self.pk)
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

    @transaction.atomic
    def confirm(self, user):
        switch = ApplicationAccountSwitch.objects.select_for_update().get(pk=self.switch_id)
        item = self.__class__.objects.select_for_update().get(pk=self.pk)
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

    @transaction.atomic
    def report(self, success, error=''):
        switch = ApplicationAccountSwitch.objects.select_for_update().get(
            pk=self.item.switch_id
        )
        event = self.__class__.objects.select_for_update().select_related(
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
