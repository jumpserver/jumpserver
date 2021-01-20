from common.utils.lock import DistributedLock


class UserGrantedTreeRebuildLock(DistributedLock):
    name_template = 'perms.user.asset.node.tree.rebuid.<org_id:{org_id}>.<user_id:{user_id}>'

    def __init__(self, org_id, user_id):
        name = self.name_template.format(
            org_id=org_id, user_id=user_id
        )
        super().__init__(name=name)
