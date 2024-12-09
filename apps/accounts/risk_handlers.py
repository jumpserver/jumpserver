from django.utils.translation import gettext_lazy as _

from common.const import ConfirmOrIgnore
from accounts.models import GatheredAccount, AccountRisk, SecretType, AutomationExecution
from django.utils import timezone

from common.const import ConfirmOrIgnore

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
    def __init__(self, asset, username, request=None, risk=''):
        self.asset = asset
        self.username = username
        self.request = request
        self.risk = risk

    def handle(self, tp, risk=''):
        self.risk = risk
        attr = f"handle_{tp}"
        if hasattr(self, attr):
            ret = getattr(self, attr)()
            self.update_risk_if_need(tp)
            return ret
        else:
            raise ValueError(f"Invalid risk type: {tp}")

    def update_risk_if_need(self, tp):
        r = self.get_risk()
        if not r:
            return
        status = ConfirmOrIgnore.ignored if tp == 'ignore' else ConfirmOrIgnore.confirmed
        r.details.append({
            **self.process_detail,
            'action': tp, 'status': status
        })
        r.status = status
        r.save()

    def get_risk(self):
        r = AccountRisk.objects.filter(asset=self.asset, username=self.username)
        if self.risk:
            r = r.filter(risk=self.risk)
        return r.first()

    def handle_ignore(self):
        GatheredAccount.objects.filter(asset=self.asset, username=self.username).update(status=ConfirmOrIgnore.ignored)
        self.risk = 'ignored'

    def handle_review(self):
        pass

    @property
    def process_detail(self):
        return {
            "datetime": timezone.now().isoformat(), "type": "process",
            "processor": str(self.request.user)
        }

    def handle_add_account(self):
        data = {
            "username": self.username,
            "name": self.username,
            "secret_type": SecretType.PASSWORD,
            "source": "collected",
        }
        self.asset.accounts.get_or_create(defaults=data, username=self.username)
        GatheredAccount.objects.filter(asset=self.asset, username=self.username).update(
            present=True, status=ConfirmOrIgnore.confirmed
        )
        self.risk = 'new_found'

    def handle_disable_remote(self):
        pass

    def handle_delete_remote(self):
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
        return execution.summary

    def handle_delete_both(self):
        pass

    def handle_change_password_add(self):
        pass

    def handle_change_password(self):
        pass
