import hashlib
import os
import re
import sqlite3
import uuid

from django.conf import settings
from django.utils import timezone

from accounts.models import Account, AccountRisk, RiskChoice
from assets.automations.base.manager import BaseManager
from common.const import ConfirmOrIgnore
from common.decorators import bulk_create_decorator, bulk_update_decorator


@bulk_create_decorator(AccountRisk)
def create_risk(data):
    return AccountRisk(**data)


@bulk_update_decorator(AccountRisk, update_fields=["details", "status"])
def update_risk(risk):
    return risk


class BaseCheckHandler:
    risk = ''

    def __init__(self, assets):
        self.assets = assets

    def check(self, account):
        pass

    def clean(self):
        pass


class CheckSecretHandler(BaseCheckHandler):
    risk = RiskChoice.weak_password

    @staticmethod
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

    def check(self, account):
        if not account.secret:
            return False
        return self.is_weak_password(account.secret)


class CheckRepeatHandler(BaseCheckHandler):
    risk = RiskChoice.repeated_password

    def __init__(self, assets):
        super().__init__(assets)
        self.path, self.conn, self.cursor = self.init_repeat_check_db()
        self.add_password_for_check_repeat()

    @staticmethod
    def init_repeat_check_db():
        path = os.path.join('/tmp', 'accounts_' + str(uuid.uuid4()) + '.db')
        sql = """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            digest CHAR(32)
        )
        """
        index = "CREATE INDEX IF NOT EXISTS idx_digest ON accounts(digest)"
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute(sql)
        cursor.execute(index)
        return path, conn, cursor

    def check(self, account):
        if not account.secret:
            return False

        digest = self.digest(account.secret)
        sql = 'SELECT COUNT(*) FROM accounts WHERE digest = ?'
        self.cursor.execute(sql, [digest])
        result = self.cursor.fetchone()
        if not result:
            return False
        return result[0] > 1

    @staticmethod
    def digest(secret):
        return hashlib.md5(secret.encode()).hexdigest()

    def add_password_for_check_repeat(self):
        accounts = Account.objects.all().only('id', '_secret', 'secret_type')
        sql = "INSERT INTO accounts (digest) VALUES (?)"

        for account in accounts:
            secret = account.secret
            if not secret:
                continue
            digest = self.digest(secret)
            self.cursor.execute(sql, [digest])
        self.conn.commit()

    def clean(self):
        self.cursor.close()
        self.conn.close()
        os.remove(self.path)


class CheckLeakHandler(BaseCheckHandler):
    risk = RiskChoice.leaked_password

    def __init__(self, *args):
        super().__init__(*args)
        self.conn, self.cursor = self.init_leak_password_db()

    @staticmethod
    def init_leak_password_db():
        db_path = os.path.join(
            settings.APPS_DIR, 'accounts', 'automations',
            'check_account', 'leak_passwords.db'
        )

        if settings.LEAK_PASSWORD_DB_PATH and os.path.isfile(settings.LEAK_PASSWORD_DB_PATH):
            db_path = settings.LEAK_PASSWORD_DB_PATH

        db_conn = sqlite3.connect(db_path)
        db_cursor = db_conn.cursor()
        return db_conn, db_cursor

    def check(self, account):
        if not account.secret:
            return False

        sql = 'SELECT 1 FROM passwords WHERE password = ? LIMIT 1'
        self.cursor.execute(sql, (account.secret,))
        leak = self.cursor.fetchone() is not None
        return leak

    def clean(self):
        self.cursor.close()
        self.conn.close()


class CheckAccountManager(BaseManager):
    batch_size = 100
    tmpl = 'Checked the status of account %s: %s'

    def __init__(self, execution):
        super().__init__(execution)
        self.assets = []
        self.batch_risks = []
        self.handlers = []

    def add_risk(self, risk, account):
        self.summary[risk] += 1
        self.result[risk].append({
            'asset': str(account.asset), 'username': account.username,
        })
        risk_obj = {'account': account, 'risk': risk}
        self.batch_risks.append(risk_obj)

    def commit_risks(self, assets):
        account_risks = AccountRisk.objects.filter(asset__in=assets)
        ori_risk_map = {}

        for risk in account_risks:
            key = f'{risk.account_id}_{risk.risk}'
            ori_risk_map[key] = risk

        now = timezone.now().isoformat()
        for d in self.batch_risks:
            account = d["account"]
            key = f'{account.id}_{d["risk"]}'
            origin_risk = ori_risk_map.get(key)

            if origin_risk and origin_risk.status != ConfirmOrIgnore.pending:
                details = origin_risk.details or []
                details.append({"datetime": now, 'type': 'refind'})

                if len(details) > 10:
                    details = [*details[:5], *details[-5:]]

                origin_risk.details = details
                origin_risk.status = ConfirmOrIgnore.pending
                update_risk(origin_risk)
            else:
                create_risk({
                    "account": account,
                    "asset": account.asset,
                    "username": account.username,
                    "risk": d["risk"],
                    "details": [{"datetime": now, 'type': 'init'}],
                })

    def pre_run(self):
        super().pre_run()
        self.assets = self.execution.get_all_assets()
        self.execution.date_start = timezone.now()
        self.execution.save(update_fields=["date_start"])

    def batch_check(self, handler):
        print("Engine: {}".format(handler.__class__.__name__))
        for i in range(0, len(self.assets), self.batch_size):
            _assets = self.assets[i: i + self.batch_size]
            accounts = Account.objects.filter(asset__in=_assets)

            print("Start to check accounts: {}".format(len(accounts)))

            for account in accounts:
                error = handler.check(account)
                msg = handler.risk if error else 'ok'

                print("Check: {} => {}".format(account, msg))
                if not error:
                    continue
                self.add_risk(handler.risk, account)
            self.commit_risks(_assets)

    def do_run(self, *args, **kwargs):
        for engine in self.execution.snapshot.get("engines", []):
            if engine == "check_account_secret":
                handler = CheckSecretHandler(self.assets)
            elif engine == "check_account_repeat":
                handler = CheckRepeatHandler(self.assets)
            elif engine == "check_account_leak":
                handler = CheckLeakHandler(self.assets)
            else:
                print("Unknown engine: {}".format(engine))
                continue

            self.handlers.append(handler)
            self.batch_check(handler)

    def post_run(self):
        super().post_run()
        for handler in self.handlers:
            handler.clean()

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
