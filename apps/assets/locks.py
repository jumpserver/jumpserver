from orgs.utils import current_org
from common.utils.lock import DistributedLock


class NodeTreeUpdateLock(DistributedLock):
    name_template = 'assets.node.tree.update.<org_id:{org_id}>'

    def get_name(self):
        if current_org:
            org_id = current_org.id
        else:
            org_id = 'current_org_is_null'
        name = self.name_template.format(
            org_id=org_id
        )
        return name

    def __init__(self):
        name = self.get_name()
        super().__init__(name=name, release_on_transaction_commit=True, reentrant=True)
