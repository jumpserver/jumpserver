from django.conf import settings
from django.db import migrations, models, transaction
import django.db.models.deletion
import tickets.models.ticket
import uuid

ticket_assignee_m2m = list()


def get_ticket_assignee_m2m_info(apps, schema_editor):
    ticket_model = apps.get_model("tickets", "Ticket")
    for i in ticket_model.objects.only('id', 'assignees', 'action', 'created_by'):
        ticket_assignee_m2m.append((i.id, list(i.assignees.values_list('id', flat=True)), i.action, i.created_by))


def create_ticket_assignee_m2m_info(apps, schema_editor):
    ticket_assignee_model = apps.get_model("tickets", "TicketAssignee")
    creates = list()
    with transaction.atomic():
        for id, assignees, action, created_by in ticket_assignee_m2m:
            for assignee_id in assignees:
                creates.append(
                    ticket_assignee_model(
                        ticket_id=id, user_id=assignee_id, is_processor=True, action=action, created_by=created_by
                    )
                )
        ticket_assignee_model.objects.bulk_create(creates)