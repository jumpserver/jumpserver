from copy import deepcopy
from collections import defaultdict

from ..base.manager import BasePlaybookManager


class ChangePasswordManager(BasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.method_hosts_mapper = defaultdict(list)
        self.playbooks = []

    @classmethod
    def method_type(cls):
        return 'change_password'

    def host_callback(self, host, asset=None, account=None, automation=None, **kwargs):
        host = super().host_callback(host, asset=asset, account=account, automation=automation, **kwargs)
        if host.get('exclude'):
            return host

        accounts = asset.accounts.all()
        if account:
            accounts = accounts.exclude(id=account.id)

        if '*' not in self.automation.accounts:
            accounts = accounts.filter(username__in=self.automation.accounts)

        method_attr = getattr(automation, self.method_type() + '_method')
        method_hosts = self.method_hosts_mapper[method_attr]
        method_hosts = [h for h in method_hosts if h != host['name']]
        inventory_hosts = []
        for account in accounts:
            h = deepcopy(host)
            h['name'] += '_' + account.username
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': account.secret,
            }
            inventory_hosts.append(h)
            method_hosts.append(h['name'])
        self.method_hosts_mapper[method_attr] = method_hosts
        return inventory_hosts

    def on_runner_done(self, runner, cb):
        pass

    def on_runner_failed(self, runner, e):
        pass


