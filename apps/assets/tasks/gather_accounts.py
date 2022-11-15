# ~*~ coding: utf-8 ~*~
from celery import shared_task
from django.utils.translation import gettext_noop
from django.utils.translation import gettext_lazy as _

from orgs.utils import tmp_to_root_org, org_aware_func
from common.utils import get_logger
from assets.models import Node

__all__ = ['gather_asset_accounts']
logger = get_logger(__name__)


@org_aware_func("nodes")
def gather_asset_accounts_util(nodes, task_name):
    from assets.models import GatherAccountsAutomation
    task_name = GatherAccountsAutomation.generate_unique_name(task_name)

    data = {
        'name': task_name,
        'comment': ', '.join([str(i) for i in nodes])
    }
    instance = GatherAccountsAutomation.objects.create(**data)
    instance.nodes.add(*nodes)
    instance.execute()


@shared_task(queue="ansible", verbose_name=_('Gather asset accounts'))
def gather_asset_accounts(node_ids, task_name=None):
    if task_name is None:
        task_name = gettext_noop("Gather assets accounts")

    with tmp_to_root_org():
        nodes = Node.objects.filter(id__in=node_ids)
    gather_asset_accounts_util(nodes=nodes, task_name=task_name)
