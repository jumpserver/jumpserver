import re
import time
from collections import defaultdict

from django.template.loader import render_to_string
from django.utils import timezone
from premailer import transform

from accounts.models import Account, AccountRisk
from common.db.utils import safe_db_connection
from common.tasks import send_mail_async
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
    if (not re.search(r'[A-Za-z]', password)
            or not re.search(r'[0-9]', password)
            or not re.search(r'[\W_]', password)):
        return True
    return False


def check_account_secrets(accounts, assets):
    now = timezone.now().isoformat()
    risks = []
    tmpl = "Check account %s: %s"
    summary = defaultdict(int)
    result = defaultdict(list)
    summary['accounts'] = len(accounts)
    summary['assets'] = len(assets)

    for account in accounts:
        result_item = {
            'asset': str(account.asset),
            'username': account.username,
        }
        if not account.secret:
            print(tmpl % (account, "no secret"))
            summary['no_secret'] += 1
            result['no_secret'].append(result_item)
            continue

        if is_weak_password(account.secret):
            print(tmpl % (account, color_fmt("weak", "red")))
            summary['weak_password'] += 1
            result['weak_password'].append(result_item)
            risks.append({
                'account': account,
                'risk': 'weak_password',
            })
        else:
            summary['ok'] += 1
            result['ok'].append(result_item)
            print(tmpl % (account, color_fmt("ok", "green")))

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
    return summary, result


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
        self.result = defaultdict(list)

    def pre_run(self):
        self.assets = self.execution.get_all_assets()
        self.execution.date_start = timezone.now()
        self.execution.save(update_fields=['date_start'])

    def batch_run(self, batch_size=100):
        for engine in self.execution.snapshot.get('engines', []):
            if engine == 'check_account_secret':
                handle = check_account_secrets
            else:
                continue

            for i in range(0, len(self.assets), batch_size):
                _assets = self.assets[i:i + batch_size]
                accounts = Account.objects.filter(asset__in=_assets)
                summary, result = handle(accounts, _assets)

                for k, v in summary.items():
                    self.summary[k] = self.summary.get(k, 0) + v
                for k, v in result.items():
                    self.result[k].extend(v)

    def _update_execution_and_summery(self):
        self.date_end = timezone.now()
        self.time_end = time.time()
        self.duration = self.time_end - self.time_start
        self.execution.date_finished = timezone.now()
        self.execution.status = 'success'
        self.execution.summary = self.summary
        self.execution.result = self.result

        with safe_db_connection():
            self.execution.save(update_fields=['date_finished', 'status', 'summary', 'result'])

    def after_run(self):
        self._update_execution_and_summery()
        self._send_report()

        tmpl = "\n---\nSummary: \nok: %s, weak password: %s, no secret: %s, using time: %ss" % (
            self.summary['ok'], self.summary['weak_password'], self.summary['no_secret'], int(self.timedelta)
        )
        print(tmpl)

    def gen_report(self):
        template_path = 'accounts/check_account_report.html'
        context = {
            'execution': self.execution,
            'summary': self.execution.summary,
            'result': self.execution.result
        }
        data = render_to_string(template_path, context)
        return data

    def _send_report(self):
        recipients = self.execution.recipients
        if not recipients:
            return

        report = self.gen_report()
        report = transform(report)
        print("Send resport to: {}".format([str(r) for r in recipients]))
        subject = f'Check account automation {self.execution.id} finished'
        emails = [r.email for r in recipients if r.email]

        send_mail_async(subject, report, emails, html_message=report)

    def run(self,):
        self.pre_run()
        self.batch_run()
        self.after_run()
