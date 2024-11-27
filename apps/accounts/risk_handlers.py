from django.utils.translation import gettext_lazy as _

from accounts.models import GatheredAccount, AccountRisk, SecretType, AutomationExecution

TYPE_CHOICES = [
    ("ignore", _("Ignore")),
    ("disable_remote", _("Disable remote")),
    ("delete_remote", _("Delete remote")),
    ("delete_both", _("Delete remote")),
    ("add_account", _("Add account")),
    ("change_password_add", _("Change password and Add")),
    ("change_password", _("Change password")),
]


class RiskHandler:
    def __init__(self, asset, username):
        self.asset = asset
        self.username = username

    def handle(self, tp, risk=""):
        attr = f"handle_{tp}"
        if hasattr(self, attr):
            return getattr(self, attr)(risk=risk)
        else:
            raise ValueError(f"Invalid risk type: {tp}")

    def handle_ignore(self, risk=""):
        pass

    def handle_add_account(self, risk=""):
        data = {
            "username": self.username,
            "name": self.username,
            "secret_type": SecretType.PASSWORD,
            "source": "collected",
        }
        self.asset.accounts.get_or_create(defaults=data, username=self.username)
        GatheredAccount.objects.filter(asset=self.asset, username=self.username).update(
            present=True, status="confirmed"
        )
        (
            AccountRisk.objects.filter(asset=self.asset, username=self.username)
            .filter(risk__in=["new_found"])
            .update(status="confirmed")
        )

    def handle_disable_remote(self, risk=""):
        pass

    def handle_delete_remote(self, risk=""):
        asset = self.asset
        execution = AutomationExecution()
        execution.snapshot = {
            "assets": [str(asset.id)],
            "accounts": [{"asset": str(asset.id), "username": self.username}],
            "type": "remove_account",
            "name": "Remove remote account: {}@{}".format(self.username, asset.name),
        }
        execution.save()
        execution.start()
        return execution

    def handle_delete_both(self, risk=""):
        pass

    def handle_change_password_add(self, risk=""):
        pass

    def handle_change_password(self, risk=""):
        pass
