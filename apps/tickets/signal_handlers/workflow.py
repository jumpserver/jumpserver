from django.db import connections
from django.db.models.signals import post_save
from django.dispatch import receiver

from orgs.models import Organization


@receiver(post_save, sender=Organization)
def initialize_organization_workflows(sender, instance, created, using, raw=False, **kwargs):
    if not created or raw or using != 'default' or str(instance.pk) in (Organization.ROOT_ID, Organization.SYSTEM_ID):
        return
    # Organizations can also be created before the workflow schema is installed.
    if 'tickets_workflow' not in connections[using].introspection.table_names():
        return
    from tickets.workflow.initialization import ensure_default_workflows
    ensure_default_workflows([str(instance.pk)])
