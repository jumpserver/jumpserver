from django.db import models
from django.db.models import Model


class TicketSession(Model):
    ticket = models.ForeignKey('tickets.Ticket', related_name='session_relation', on_delete=models.CASCADE, db_constraint=False)
    session = models.ForeignKey('terminal.Session', related_name='ticket_relation', on_delete=models.CASCADE, db_constraint=False)

    @classmethod
    def get_ticket_by_session_id(cls, session_id):
        relation = cls.objects.filter(session=session_id).first()
        if relation:
            return relation.ticket
        return None
