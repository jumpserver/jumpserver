from django.db import models
from django.utils.translation import gettext_lazy as _


class TicketSession(models.Model):
    ticket = models.ForeignKey('tickets.Ticket', related_name='session_relation', on_delete=models.CASCADE,
                               db_constraint=False)
    session = models.ForeignKey('terminal.Session', related_name='ticket_relation', on_delete=models.CASCADE,
                                db_constraint=False)

    class Meta:
        verbose_name = _("Ticket session relation")

    @classmethod
    def get_ticket_by_session_id(cls, session_id):
        relation = cls.objects.filter(session=session_id).first()
        if relation:
            return relation.ticket
        return None


class TicketBeneficiary(models.Model):
    """People who receive an approved ticket's result, independent of its applicant."""
    ticket = models.ForeignKey('tickets.Ticket', related_name='beneficiaries', on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', related_name='benefiting_tickets', on_delete=models.CASCADE)

    class Meta:
        default_permissions = ()
        unique_together = (('ticket', 'user'),)
        verbose_name = _('Ticket beneficiary')


class TicketSecretAccess(models.Model):
    """An approved, account-scoped opportunity to reveal a password."""
    id = models.BigAutoField(primary_key=True)
    ticket = models.ForeignKey('tickets.Ticket', related_name='secret_accesses', on_delete=models.CASCADE)
    account_id = models.UUIDField()
    user_id = models.UUIDField()
    org_id = models.CharField(max_length=36)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=['ticket', 'account_id'], name='tickets_secret_ticket_account_uniq')]
        indexes = [models.Index(fields=['user_id', 'expires_at'], name='tickets_secret_user_expire')]
