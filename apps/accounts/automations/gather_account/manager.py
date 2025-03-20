from collections import defaultdict

import time
from django.utils import timezone

from accounts.const import AutomationTypes
from accounts.models import GatheredAccount, Account, AccountRisk, RiskChoice
from common.const import ConfirmOrIgnore
from common.decorators import bulk_create_decorator, bulk_update_decorator
from common.utils import get_logger
from common.utils.strings import get_text_diff
from orgs.utils import tmp_to_org
from .filter import GatherAccountsFilter
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)

risk_items = [
    "authorized_keys",
    "sudoers",
    "groups",
]
common_risk_items = [
    "address_last_login",
    "date_last_login",
    "date_password_change",
    "date_password_expired",
    "detail"
]
diff_items = risk_items + common_risk_items


def format_datetime(value):
    if isinstance(value, timezone.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def get_items_diff(ori_account, d):
    if hasattr(ori_account, "_diff"):
        return ori_account._diff

    diff = {}
    for item in diff_items:
        get_item_diff(item, ori_account, d, diff)
    ori_account._diff = diff
    return diff


def get_item_diff(item, ori_account, d, diff):
    detail = getattr(ori_account, 'detail', {})
    new_detail = d.get('detail', {})
    ori = getattr(ori_account, item, None) or detail.get(item)
    new = d.get(item, "") or new_detail.get(item)
    if not ori and not new:
        return

    ori = format_datetime(ori)
    new = format_datetime(new)

    if new != ori:
        diff[item] = get_text_diff(str(ori), str(new))


class AnalyseAccountRisk:
    long_time = timezone.timedelta(days=90)
    datetime_check_items = [
        {"field": "date_last_login", "risk": "long_time_no_login", "delta": long_time},
        {
            "field": "date_password_change",
            "risk": RiskChoice.long_time_password,
            "delta": long_time,
        },
        {
            "field": "date_password_expired",
            "risk": "password_expired",
            "delta": timezone.timedelta(seconds=1),
        },
    ]

    def __init__(self, check_risk=True):
        self.check_risk = check_risk
        self.now = timezone.now()
        self.pending_add_risks = []

    def _analyse_item_changed(self, ori_ga, d):
        diff = get_items_diff(ori_ga, d)
        if not diff:
            return

        risks = []
        for k, v in diff.items():
            if k not in risk_items:
                continue
            risks.append(
                dict(
                    asset_id=str(ori_ga.asset_id),
                    username=ori_ga.username,
                    gathered_account=ori_ga,
                    risk=k + "_changed",
                    detail={"diff": v},
                )
            )
        self.save_or_update_risks(risks)

    def _analyse_datetime_changed(self, ori_account, d, asset, username):
        basic = {"asset_id": str(asset.id), "username": username}

        risks = []
        for item in self.datetime_check_items:
            field = item["field"]
            risk = item["risk"]
            delta = item["delta"]

            date = d.get(field)
            if not date:
                continue

            # 服务器收集的时间和数据库时间一致，不进行比较，无法检测风险 不太对，先注释
            # pre_date = ori_account and getattr(ori_account, field)
            # if pre_date == date:
            #     continue

            if date and date < timezone.now() - delta:
                risks.append(
                    dict(**basic, risk=risk, detail={"date": date.isoformat()})
                )

        self.save_or_update_risks(risks)

    def save_or_update_risks(self, risks):
        # 提前取出来，避免每次都查数据库
        asset_ids = {r["asset_id"] for r in risks}
        assets_risks = AccountRisk.objects.filter(asset_id__in=asset_ids)
        assets_risks = {f"{r.asset_id}_{r.username}_{r.risk}": r for r in assets_risks}

        for d in risks:
            detail = d.pop("detail", {})
            detail["datetime"] = self.now.isoformat()
            key = f"{d['asset_id']}_{d['username']}_{d['risk']}"
            found = assets_risks.get(key)

            if not found:
                self._create_risk(dict(**d, details=[detail]))
                continue

            found.details.append(detail)
            self._update_risk(found)

    @bulk_create_decorator(AccountRisk)
    def _create_risk(self, data):
        return AccountRisk(**data)

    @bulk_update_decorator(AccountRisk, update_fields=["details"])
    def _update_risk(self, account):
        return account

    def lost_accounts(self, asset, lost_users):
        if not self.check_risk:
            return
        for user in lost_users:
            self._create_risk(
                dict(
                    asset_id=str(asset.id),
                    username=user,
                    risk=RiskChoice.account_deleted,
                    details=[{"datetime": self.now.isoformat()}],
                )
            )

    def analyse_risk(self, asset, ga, d, sys_found):
        if not self.check_risk:
            return

        if ga:
            self._analyse_item_changed(ga, d)
        if not sys_found:
            basic = {"asset": asset, "username": d["username"], 'gathered_account': ga}
            self._create_risk(
                dict(
                    **basic,
                    risk=RiskChoice.new_found,
                    details=[{"datetime": self.now.isoformat()}],
                )
            )
        self._analyse_datetime_changed(ga, d, asset, d["username"])


class GatherAccountsManager(AccountBasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_mapper = {}
        self.asset_account_info = {}
        self.asset_usernames_mapper = defaultdict(set)
        self.ori_asset_usernames = defaultdict(set)
        self.ori_gathered_usernames = defaultdict(set)
        self.ori_gathered_accounts_mapper = dict()
        self.is_sync_account = self.execution.snapshot.get("is_sync_account")
        self.check_risk = self.execution.snapshot.get("check_risk", False)

    @classmethod
    def method_type(cls):
        return AutomationTypes.gather_accounts

    def host_callback(self, host, asset=None, **kwargs):
        super().host_callback(host, asset=asset, **kwargs)
        self.host_asset_mapper[host["name"]] = asset
        return host

    def _filter_success_result(self, tp, result):
        result = GatherAccountsFilter(tp).run(self.method_id_meta_mapper, result)
        return result

    @staticmethod
    def _get_nested_info(data, *keys):
        for key in keys:
            data = data.get(key, {})
            if not data:
                break
        return data

    def _collect_asset_account_info(self, asset, info):
        result = self._filter_success_result(asset.type, info)
        accounts = []
        for username, info in result.items():
            self.asset_usernames_mapper[str(asset.id)].add(username)

            d = {"asset": asset, "username": username, "remote_present": True, **info}
            accounts.append(d)
        self.asset_account_info[asset] = accounts

    def on_host_success(self, host, result):
        super().on_host_success(host, result)
        info = self._get_nested_info(result, "debug", "res", "info")
        asset = self.host_asset_mapper.get(host)

        if asset and info:
            self._collect_asset_account_info(asset, info)
        else:
            print(f"\033[31m Not found {host} info \033[0m\n")

    def prefetch_origin_account_usernames(self):
        """
        提起查出来，避免每次 sql 查询
        :return:
        """
        assets = self.asset_usernames_mapper.keys()
        accounts = Account.objects.filter(asset__in=assets).values_list(
            "asset", "username"
        )

        for asset_id, username in accounts:
            self.ori_asset_usernames[str(asset_id)].add(username)

        ga_accounts = GatheredAccount.objects.filter(asset__in=assets)
        for account in ga_accounts:
            self.ori_gathered_usernames[str(account.asset_id)].add(account.username)
            key = "{}_{}".format(account.asset_id, account.username)
            self.ori_gathered_accounts_mapper[key] = account

    def update_gather_accounts_status(self, asset):
        """
        远端账号，收集中的账号，vault 中的账号。
        要根据账号新增见啥，标识 收集账号的状态, 让管理员关注

        远端账号 -> 收集账号 -> 特权账号
        """
        remote_users = self.asset_usernames_mapper[str(asset.id)]
        ori_users = self.ori_asset_usernames[str(asset.id)]
        ori_ga_users = self.ori_gathered_usernames[str(asset.id)]

        queryset = GatheredAccount.objects.filter(asset=asset).exclude(
            status=ConfirmOrIgnore.ignored
        )

        # 远端账号 比 收集账号多的
        # 新增创建，不用处理状态
        new_found_users = remote_users - ori_ga_users
        if new_found_users:
            self.summary["new_accounts"] += len(new_found_users)
            for username in new_found_users:
                self.result["new_accounts"].append(
                    {
                        "asset": str(asset),
                        "username": username,
                    }
                )

        # 远端上 比 收集账号少的
        # 标识 remote_present=False, 标记为待处理
        # 远端资产上不存在的，标识为待处理，需要管理员介入
        lost_users = ori_ga_users - remote_users
        if lost_users:
            queryset.filter(username__in=lost_users).update(
                status=ConfirmOrIgnore.pending, remote_present=False
            )
            self.summary["lost_accounts"] += len(lost_users)
            for username in lost_users:
                self.result["lost_accounts"].append(
                    {
                        "asset": str(asset),
                        "username": username,
                    }
                )
            risk_analyser = AnalyseAccountRisk(self.check_risk)
            risk_analyser.lost_accounts(asset, lost_users)

        # 收集的账号 比 账号列表多的, 有可能是账号中删掉了, 但这时候状态已经是 confirm 了
        # 标识状态为 待处理, 让管理员去确认
        ga_added_users = ori_ga_users - ori_users
        if ga_added_users:
            queryset.filter(username__in=ga_added_users).update(status=ConfirmOrIgnore.pending)

        # 收集的账号 比 账号列表少的
        # 这个好像不不用对比，原始情况就这样

        # 远端账号 比 账号列表少的
        # 创建收集账号，标识 remote_present=False, 状态待处理

        # 远端账号 比 账号列表多的
        # 正常情况, 不用处理，因为远端账号会创建到收集账号，收集账号再去对比

        # 不过这个好像也处理一下 status，因为已存在，这是状态应该是确认
        (
            queryset.filter(username__in=ori_users)
            .exclude(status=ConfirmOrIgnore.confirmed)
            .update(status=ConfirmOrIgnore.confirmed)
        )

        # 远端存在的账号，标识为已存在
        (
            queryset.filter(username__in=remote_users, remote_present=False).update(
                remote_present=True
            )
        )

        # 资产上没有的，标识为为存在
        (
            queryset.exclude(username__in=ori_users)
            .filter(present=True)
            .update(present=False)
        )
        (
            queryset.filter(username__in=ori_users)
            .filter(present=False)
            .update(present=True)
        )

    @bulk_create_decorator(GatheredAccount)
    def create_gathered_account(self, d):
        ga = GatheredAccount()
        for k, v in d.items():
            setattr(ga, k, v)

        return ga

    @bulk_update_decorator(GatheredAccount, update_fields=common_risk_items)
    def update_gathered_account(self, ori_account, d):
        diff = get_items_diff(ori_account, d)
        if not diff:
            return
        for k in diff:
            if k not in common_risk_items:
                continue
            v = d.get(k)
            setattr(ori_account, k, v)
        return ori_account

    def do_run(self, *args, **kwargs):
        super().do_run(*args, **kwargs)
        self.prefetch_origin_account_usernames()
        risk_analyser = AnalyseAccountRisk(self.check_risk)

        for asset, accounts_data in self.asset_account_info.items():
            ori_users = self.ori_asset_usernames[str(asset.id)]
            with tmp_to_org(asset.org_id):
                for d in accounts_data:
                    username = d["username"]
                    ori_account = self.ori_gathered_accounts_mapper.get(
                        "{}_{}".format(asset.id, username)
                    )
                    if not ori_account:
                        ga = self.create_gathered_account(d)
                    else:
                        ga = ori_account
                        self.update_gathered_account(ori_account, d)
                    ori_found = username in ori_users
                    risk_analyser.analyse_risk(asset, ga, d, ori_found)

                self.create_gathered_account.finish()
                self.update_gathered_account.finish()
                self.update_gather_accounts_status(asset)
                if not self.is_sync_account:
                    continue
                gathered_accounts = GatheredAccount.objects.filter(asset=asset)
                GatheredAccount.sync_accounts(gathered_accounts)
                GatheredAccount.objects.filter(
                    asset=asset, username__in=ori_users, present=False
                ).update(
                    present=True
                )
        # 因为有 bulk create, bulk update, 所以这里需要 sleep 一下，等待数据同步
        time.sleep(0.5)

    def get_report_template(self):
        return "accounts/gather_account_report.html"
