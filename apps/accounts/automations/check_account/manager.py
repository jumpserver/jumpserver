import os
import re

from collections import defaultdict

from django.conf import settings
from django.utils import timezone

from accounts.models import Account, AccountRisk, RiskChoice
from assets.automations.base.manager import BaseManager
from common.decorators import bulk_create_decorator, bulk_update_decorator
from common.utils.strings import color_fmt


def is_weak_password(password):
    # 判断密码长度
    if len(password) < 8:
        return True

    # 判断是否只有一种字符类型
    if password.isdigit() or password.isalpha():
        return True

    # 判断是否只包含数字或字母
    if password.islower() or password.isupper():
        return True

    # 判断是否包含常见弱密码
    common_passwords = ["123456", "password", "12345678", "qwerty", "abc123"]
    if password.lower() in common_passwords:
        return True

    # 正则表达式判断字符多样性（数字、字母、特殊字符）
    if (
        not re.search(r"[A-Za-z]", password)
        or not re.search(r"[0-9]", password)
        or not re.search(r"[\W_]", password)
    ):
        return True
    return False


@bulk_create_decorator(AccountRisk)
def create_risk(data):
    return AccountRisk(**data)


@bulk_update_decorator(AccountRisk, update_fields=["details"])
def update_risk(risk):
    return risk


class CheckAccountManager(BaseManager):
    batch_size = 100
    tmpl = 'Checked the status of account %s: %s'

    def __init__(self, execution):
        super().__init__(execution)
        self.accounts = []
        self.assets = []
        self._leak_pwd_set = set()
        self.global_origin_risks_dict = dict()

    def load_leak_pwd_set(self):
        path = os.path.join(
            settings.APPS_DIR, 'accounts', 'automations', 'check_account', 'leak_password.txt'
        )
        file = open(path, 'r')
        for line in file.readlines():
            self._leak_pwd_set.add(line.strip())
        file.close()

    @staticmethod
    def create_or_update_risk(risks, origin_risks_dict):
        now = timezone.now().isoformat()
        for d in risks:
            key = f'{d["account"].asset_id}_{d["account"].username}_{d["risk"]}'
            origin_risk = origin_risks_dict.get(key)

            if origin_risk:
                origin_risk.details.append({"datetime": now, 'type': 'refind'})
                update_risk(origin_risk)
            else:
                create_risk({
                    "asset": d["account"].asset,
                    "username": d["account"].username,
                    "risk": d["risk"],
                    "details": [{"datetime": now, 'type': 'init'}],
                })

    def check_account_secrets(self, accounts, assets):
        risks = []
        for account in accounts:
            if not account.secret:
                print(self.tmpl % (account, "no secret"))
                self.risk_record('no_secret', account)
                continue

            if is_weak_password(account.secret):
                key = RiskChoice.weak_password
                print(self.tmpl % (account, color_fmt(key.value, "red")))
                risks.append(self.risk_record(key, account))
            elif account.secret in self._leak_pwd_set:
                key = RiskChoice.leaked_password
                print(self.tmpl % (account, color_fmt(key.value, "red")))
                risks.append(self.risk_record(key, account))
            else:
                self.accounts.append(account)

        origin_risks = AccountRisk.objects.filter(asset__in=assets)
        origin_risks_dict = {f"{r.asset_id}_{r.username}_{r.risk}": r for r in origin_risks}
        self.global_origin_risks_dict.update(origin_risks_dict)
        self.create_or_update_risk(risks, origin_risks_dict)

    def risk_record(self, key, account):
        self.summary[key] += 1
        self.result[key].append({
            'asset': str(account.asset), 'username': account.username,
        })
        return {'account': account, 'risk': key}

    def check_repeat_secrets(self):
        grouped_accounts = defaultdict(list)
        risks = []
        for account in self.accounts:
            grouped_accounts[account.secret].append(account)

        for secret, accounts in grouped_accounts.items():
            if len(accounts) >= 2:
                key = RiskChoice.repeated_password
                for a in accounts:
                    print(self.tmpl % (a, color_fmt(key.value, "red")))
                    risks.append(self.risk_record(key, a))
            else:
                key = 'ok'
                print(self.tmpl % (accounts[0], color_fmt("ok", "green")))
                self.risk_record(key, accounts[0])
        self.create_or_update_risk(risks, self.global_origin_risks_dict)

    def pre_run(self):
        self.load_leak_pwd_set()
        self.assets = self.execution.get_all_assets()
        self.execution.date_start = timezone.now()
        self.execution.save(update_fields=["date_start"])

    def do_run(self, *args, **kwargs):
        for engine in self.execution.snapshot.get("engines", []):
            if engine == "check_account_secret":
                batch_handle = self.check_account_secrets
                global_handle = self.check_repeat_secrets
            else:
                continue

            for i in range(0, len(self.assets), self.batch_size):
                _assets = self.assets[i: i + self.batch_size]
                accounts = Account.objects.filter(asset__in=_assets)
                batch_handle(accounts, _assets)

            global_handle()

    def get_report_subject(self):
        return "Check account report of %s" % self.execution.id

    def get_report_template(self):
        return "accounts/check_account_report.html"

    def print_summary(self):
        tmpl = (
            "\n---\nSummary: \nok: %s, weak password: %s, leaked password: %s, "
            "repeated password: %s, no secret: %s, using time: %ss"
            % (
                self.summary["ok"],
                self.summary[RiskChoice.weak_password],
                self.summary[RiskChoice.leaked_password],
                self.summary[RiskChoice.repeated_password],
                self.summary["no_secret"],
                int(self.duration),
            )
        )
        print(tmpl)
