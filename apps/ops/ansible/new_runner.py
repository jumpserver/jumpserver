import ansible_runner


class AnsibleInventory:
    def __init__(self, assets, account=None, ansible_connection='ssh'):
        self.assets = assets
        self.account = account


class AdHocRunner:
    pass


class PlaybookRunner:
    pass
