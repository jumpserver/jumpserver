import re
import time
from collections import defaultdict

from django.utils import timezone

from accounts.models import Account, AccountRisk


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
    if (not re.search(r'[A-Za-z]', password)
            or not re.search(r'[0-9]', password)
            or not re.search(r'[\W_]', password)):
        return True

    return False


def check_account_secrets(accounts, assets):
    now = timezone.now().isoformat()
    risks = []
    tmpl = "Check account %s: %s"
    RED = "\033[31m"
    GREEN = "\033[32m"
    RESET = "\033[0m"  # 还原默认颜色

    summary = defaultdict(int)
    for account in accounts:
        if not account.secret:
            print(tmpl % (account, "no secret"))
            summary['no_secret'] += 1
            continue

        if is_weak_password(account.secret):
            print(tmpl % (account, f"{RED}weak{RESET}"))
            summary['weak'] += 1
            risks.append({
                'account': account,
                'risk': 'weak_password',
            })
        else:
            summary['ok'] += 1
            print(tmpl % (account, f"{GREEN}ok{RESET}"))

    origin_risks = AccountRisk.objects.filter(asset__in=assets)
    origin_risks_dict = {f'{r.asset_id}_{r.username}_{r.risk}': r for r in origin_risks}

    for d in risks:
        key = f'{d["account"].asset_id}_{d["account"].username}_{d["risk"]}'
        origin_risk = origin_risks_dict.get(key)

        if origin_risk:
            origin_risk.details.append({'datetime': now})
            origin_risk.save(update_fields=['details'])
        else:
            AccountRisk.objects.create(
                asset=d['account'].asset,
                username=d['account'].username,
                risk=d['risk'],
                details=[{'datetime': now}],
            )
    return summary


class CheckAccountManager:
    def __init__(self, execution):
        self.execution = execution
        self.date_start = timezone.now()
        self.time_start = time.time()
        self.date_end = None
        self.time_end = None
        self.timedelta = 0
        self.assets = []
        self.summary = {}

    def pre_run(self):
        self.assets = self.execution.get_all_assets()

    def batch_run(self, batch_size=100):
        for engine in self.execution.snapshot.get('engines', []):
            if engine == 'check_account_secret':
                handle = check_account_secrets
            else:
                continue

            for i in range(0, len(self.assets), batch_size):
                _assets = self.assets[i:i + batch_size]
                accounts = Account.objects.filter(asset__in=_assets)
                summary = handle(accounts, _assets)
                self.summary.update(summary)

    def after_run(self):
        self.date_end = timezone.now()
        self.time_end = time.time()
        self.timedelta = self.time_end - self.time_start
        tmpl = "\n-\nSummary: ok: %s, weak: %s, no_secret: %s, using time: %ss" % (
            self.summary['ok'], self.summary['weak'], self.summary['no_secret'], self.timedelta
        )
        print(tmpl)

    def run(self,):
        self.pre_run()
        self.batch_run()
        self.after_run()
