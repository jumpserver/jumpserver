# ~*~ coding: utf-8 ~*~

from common.utils import get_logger

# __all__ = ['gather_asset_accounts_task']
logger = get_logger(__name__)

#
# @org_aware_func("nodes")
# def gather_asset_accounts_util(nodes, task_name):
#     from accounts.models import GatherAccountsAutomation
#     task_name = GatherAccountsAutomation.generate_unique_name(task_name)
#
#     task_snapshot = {
#         'nodes': [str(node.id) for node in nodes],
#     }
#     tp = AutomationTypes.verify_account
#     quickstart_automation_by_snapshot(task_name, tp, task_snapshot)
#
#
# @shared_task(
#     queue="ansible",
#     verbose_name=_('Gather asset accounts'),
#     activity_callback=lambda self, node_ids, task_name=None, *args, **kwargs: (node_ids, None),
#     description=_("Unused")
# )
# def gather_asset_accounts_task(node_ids, task_name=None):
#     if task_name is None:
#         task_name = gettext_noop("Gather assets accounts")
#
#     nodes = Node.objects.filter(id__in=node_ids)
#     gather_asset_accounts_util(nodes=nodes, task_name=task_name)
#
