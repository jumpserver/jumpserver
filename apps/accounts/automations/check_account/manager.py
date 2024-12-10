import re
from collections import defaultdict

from django.utils import timezone

from accounts.models import Account, AccountRisk
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


def check_account_secrets(accounts, assets):
    now = timezone.now().isoformat()
    risks = []
    tmpl = "Check account %s: %s"
    summary = defaultdict(int)
    result = defaultdict(list)
    summary["accounts"] = len(accounts)
    summary["assets"] = len(assets)

    for account in accounts:
        result_item = {
            "asset": str(account.asset),
            "username": account.username,
        }
        if not account.secret:
            print(tmpl % (account, "no secret"))
            summary["no_secret"] += 1
            result["no_secret"].append(result_item)
            continue

        if is_weak_password(account.secret):
            print(tmpl % (account, color_fmt("weak", "red")))
            summary["weak_password"] += 1
            result["weak_password"].append(result_item)
            risks.append(
                {
                    "account": account,
                    "risk": "weak_password",
                }
            )
        else:
            summary["ok"] += 1
            result["ok"].append(result_item)
            print(tmpl % (account, color_fmt("ok", "green")))

    origin_risks = AccountRisk.objects.filter(asset__in=assets)
    origin_risks_dict = {f"{r.asset_id}_{r.username}_{r.risk}": r for r in origin_risks}

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
    return summary, result


class CheckAccountManager(BaseManager):
    batch_size = 100

    def __init__(self, execution):
        super().__init__(execution)
        self.accounts = []
        self.assets = []

    def pre_run(self):
        self.assets = self.execution.get_all_assets()
        self.execution.date_start = timezone.now()
        self.execution.save(update_fields=["date_start"])

    def do_run(self, *args, **kwargs):
        for engine in self.execution.snapshot.get("engines", []):
            if engine == "check_account_secret":
                handle = check_account_secrets
            else:
                continue

            for i in range(0, len(self.assets), self.batch_size):
                _assets = self.assets[i: i + self.batch_size]
                accounts = Account.objects.filter(asset__in=_assets)
                summary, result = handle(accounts, _assets)

                for k, v in summary.items():
                    self.summary[k] = self.summary.get(k, 0) + v
                for k, v in result.items():
                    self.result[k].extend(v)

    def get_report_subject(self):
        return "Check account report of %s" % self.execution.id

    def get_report_template(self):
        return "accounts/check_account_report.html"

    def print_summary(self):
        tmpl = (
            "\n---\nSummary: \nok: %s, weak password: %s, no secret: %s, using time: %ss"
            % (
                self.summary["ok"],
                self.summary["weak_password"],
                self.summary["no_secret"],
                int(self.duration),
            )
        )
        print(tmpl)
