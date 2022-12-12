from common.utils.lock import DistributedLock


class UserGrantedTreeRebuildLock(DistributedLock):
    name_template = 'perms.user.asset.node.tree.rebuild.<user_id:{user_id}>'

    def __init__(self, user_id):
        name = self.name_template.format(user_id=user_id)
        super().__init__(name=name, release_on_transaction_commit=True)
