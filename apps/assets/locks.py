from orgs.utils import current_org
from babel.support import LazyProxy
from common.utils.lock import DistributedLock


class NodeTreeUpdateLock(DistributedLock):
    name_template = 'assets.node.tree.update.<org_id:{org_id}>'

    def get_name(self):
        name = self.name_template.format(
            org_id=current_org.id
        )
        return name

    def __init__(self, blocking=True):
        name = LazyProxy(self.get_name, enable_cache=False)
        super().__init__(name=name, blocking=blocking)
