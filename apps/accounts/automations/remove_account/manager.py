import os
from collections import defaultdict
from copy import deepcopy

from django.db.models import QuerySet

from accounts.const import AutomationTypes
from accounts.models import Account, GatheredAccount, AccountRisk
from common.const import ConfirmOrIgnore
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)


class RemoveAccountManager(AccountBasePlaybookManager):
    super_accounts = [
        "root", "administrator", "sa", "sys", "system", "dbsnmp",
        "postgres", "mysql",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = dict()
        self.host_accounts = defaultdict(list)
        snapshot_account = self.execution.snapshot.get("accounts", [])
        self.snapshot_asset_account_map = defaultdict(list)
        for account in snapshot_account:
            self.snapshot_asset_account_map[str(account["asset"])].append(account)

        # 给 handler 使用
        self.delete = self.execution.snapshot.get("delete", "both")
        self.confirm_risk = self.execution.snapshot.get("risk", "")

    def prepare_runtime_dir(self):
        path = super().prepare_runtime_dir()
        ansible_config_path = os.path.join(path, "ansible.cfg")

        with open(ansible_config_path, "w") as f:
            f.write("[ssh_connection]\n")
            f.write("ssh_args = -o ControlMaster=no -o ControlPersist=no\n")
        return path

    @classmethod
    def method_type(cls):
        return AutomationTypes.remove_account

    def host_callback(
        self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs
    ):
        self.ensure_unique_inventory_host(host, asset)
        if host.get("error"):
            return host

        inventory_hosts = []
        accounts_to_remove = self.snapshot_asset_account_map.get(str(asset.id), [])

        for account in accounts_to_remove:
            username = account.get("username")
            h = deepcopy(host)
            h["name"] += "(" + (username or "-") + ")"
            self.host_account_mapper[h["name"]] = account
            h["account"] = {"username": username}
            if not username:
                h["error"] = "Account username is empty"
                inventory_hosts.append(h)
                continue
            if username.lower() in self.super_accounts:
                h["error"] = "Super account can not be removed"
                inventory_hosts.append(h)
                continue
            connection_username = (
                host.get("jms_account", {}).get("username") or ""
            )
            if username.lower() == connection_username.lower():
                h["error"] = (
                    "The account used to run this automation cannot be removed"
                )
                inventory_hosts.append(h)
                continue
            inventory_hosts.append(h)
        return inventory_hosts

    def on_host_success(self, host, result):
        account = self.host_account_mapper.get(host)

        if not account:
            return super().on_host_error(
                host, 'Account mapping not found', result
            )

        try:
            if self.delete == "both":
                Account.objects.filter(
                    asset_id=account["asset"],
                    username=account["username"]
                ).delete()

            if self.confirm_risk:
                AccountRisk.objects.filter(
                    asset_id=account["asset"],
                    username=account["username"],
                    risk__in=[self.confirm_risk],
                ).update(status=ConfirmOrIgnore.confirmed)

            GatheredAccount.objects.filter(
                asset_id=account["asset"],
                username=account["username"]
            ).delete()

        except Exception as e:
            logger.exception(
                "Failed to delete account %s on asset %s",
                account['username'], account['asset'],
            )
            return super().on_host_error(host, str(e), result)
        super().on_host_success(host, result)
