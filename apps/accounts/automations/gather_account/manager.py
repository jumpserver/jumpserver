from collections import defaultdict

from django.utils import timezone

from accounts.const import AutomationTypes
from accounts.models import GatheredAccount, Account, AccountRisk
from assets.models import Asset
from common.const import ConfirmOrIgnore
from common.utils import get_logger
from common.utils.strings import get_text_diff
from orgs.utils import tmp_to_org
from users.models import User
from .filter import GatherAccountsFilter
from ..base.manager import AccountBasePlaybookManager
from ...notifications import GatherAccountChangeMsg

logger = get_logger(__name__)


class GatherAccountsManager(AccountBasePlaybookManager):
    diff_items = [
        'authorized_keys', 'sudoers', 'groups',
    ]
    long_time = timezone.timedelta(days=90)
    datetime_check_items = [
        {'field': 'date_last_login', 'risk': 'zombie', 'delta': long_time},
        {'field': 'date_password_change', 'risk': 'long_time_password', 'delta': long_time},
        {'field': 'date_password_expired', 'risk': 'password_expired', 'delta': timezone.timedelta(seconds=1)}
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_mapper = {}
        self.asset_account_info = {}

        self.asset_usernames_mapper = defaultdict(set)
        self.ori_asset_usernames = defaultdict(set)
        self.ori_gathered_usernames = defaultdict(set)
        self.ori_gathered_accounts_mapper = dict()
        self.is_sync_account = self.execution.snapshot.get('is_sync_account')
        self.pending_add_accounts = []
        self.pending_update_accounts = []
        self.pending_add_risks = []
        self.now = timezone.now()

    @classmethod
    def method_type(cls):
        return AutomationTypes.gather_accounts

    def host_callback(self, host, asset=None, **kwargs):
        super().host_callback(host, asset=asset, **kwargs)
        self.host_asset_mapper[host['name']] = asset
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
            self.asset_usernames_mapper[asset].add(username)

            d = {'asset': asset, 'username': username, 'remote_present': True, **info}
            accounts.append(d)
        self.asset_account_info[asset] = accounts

    def on_runner_failed(self,  runner, e):
        print("Runner failed: ", e)
        raise e

    def on_host_success(self, host, result):
        info = self._get_nested_info(result, 'debug', 'res', 'info')
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            self._collect_asset_account_info(asset, info)
        else:
            print(f'\033[31m Not found {host} info \033[0m\n')
            
    def prefetch_origin_account_usernames(self):
        """
        提起查出来，避免每次 sql 查询
        :return:
        """
        assets = self.asset_usernames_mapper.keys()
        accounts = Account.objects.filter(asset__in=assets).values_list('asset', 'username')

        for asset, username in accounts:
            self.ori_asset_usernames[asset].add(username)

        ga_accounts = GatheredAccount.objects.filter(asset__in=assets)
        for account in ga_accounts:
            self.ori_gathered_usernames[account.asset].add(account.username)
            key = '{}_{}'.format(account.asset.id, account.username)
            self.ori_gathered_accounts_mapper[key] = account

    def update_gather_accounts_status(self, asset):
        """
        远端账号，收集中的账号，vault 中的账号。
        要根据账号新增见啥，标识 收集账号的状态, 让管理员关注

        远端账号 -> 收集账号 -> 特权账号
        """
        remote_users = self.asset_usernames_mapper[asset]
        ori_users = self.ori_asset_usernames[asset]
        ori_ga_users = self.ori_gathered_usernames[asset]

        queryset = (GatheredAccount.objects
                    .filter(asset=asset)
                    .exclude(status=ConfirmOrIgnore.ignored))

        # 远端账号 比 收集账号多的
        # 新增创建，不用处理状态

        # 远端上 比 收集账号少的
        # 标识 remote_present=False, 标记为待处理
        # 远端资产上不存在的，标识为待处理，需要管理员介入
        lost_users = ori_ga_users - remote_users
        if lost_users:
            queryset.filter(username__in=lost_users).update(status='', remote_present=False)

        # 收集的账号 比 账号列表多的, 有可能是账号中删掉了, 但这时候状态已经是 confirm 了
        # 标识状态为 待处理, 让管理员去确认
        ga_added_users = ori_ga_users - ori_users
        if ga_added_users:
            queryset.filter(username__in=ga_added_users).update(status='')

        # 收集的账号 比 账号列表少的
        # 这个好像不不用对比，原始情况就这样

        # 远端账号 比 账号列表少的
        # 创建收集账号，标识 remote_present=False, 状态待处理

        # 远端账号 比 账号列表多的
        # 正常情况, 不用处理，因为远端账号会创建到收集账号，收集账号再去对比

        # 不过这个好像也处理一下 status，因为已存在，这是状态应该是确认
        (queryset.filter(username__in=ori_users)
         .exclude(status=ConfirmOrIgnore.confirmed)
         .update(status=ConfirmOrIgnore.confirmed))
        
        # 远端存在的账号，标识为已存在
        queryset.filter(username__in=remote_users, remote_present=False).update(remote_present=True)

        # 资产上没有的，标识为为存在
        queryset.exclude(username__in=ori_users).filter(present=False).update(present=True)

    def batch_create_gathered_account(self, d, batch_size=20):
        if d is None:
            if self.pending_add_accounts:
                GatheredAccount.objects.bulk_create(self.pending_add_accounts, ignore_conflicts=True)
                self.pending_add_accounts = []
            return

        gathered_account = GatheredAccount()
        for k, v in d.items():
            setattr(gathered_account, k, v)
        self.pending_add_accounts.append(gathered_account)

        if len(self.pending_add_accounts) > batch_size:
            self.batch_create_gathered_account(None)

    def _analyse_item_changed(self, ori_account, d):
        diff = self.get_items_diff(ori_account, d)

        if not diff:
            return

        for k, v in diff.items():
            self.pending_add_risks.append(dict(
                asset=ori_account.asset, username=ori_account.username,
                risk=k+'_changed', detail={'diff': v}
            ))

    def perform_save_risks(self, risks):
        # 提前取出来，避免每次都查数据库
        assets = {r['asset'] for r in risks}
        assets_risks = AccountRisk.objects.filter(asset__in=assets)
        assets_risks = {f"{r.asset_id}_{r.username}_{r.risk}": r for r in assets_risks}

        for d in risks:
            detail = d.pop('detail', {})
            detail['datetime'] = self.now.isoformat()
            key = f"{d['asset'].id}_{d['username']}_{d['risk']}"
            found = assets_risks.get(key)

            if not found:
                r = AccountRisk(**d, details=[detail])
                r.save()
                continue

            found.details.append(detail)
            found.save(update_fields=['details'])

    def _analyse_datetime_changed(self, ori_account, d, asset, username):
        basic = {'asset': asset, 'username': username}

        for item in self.datetime_check_items:
            field = item['field']
            risk = item['risk']
            delta = item['delta']

            date = d.get(field)
            if not date:
                continue

            pre_date = ori_account and getattr(ori_account, field)
            if pre_date == date:
                continue

            if date and date < timezone.now() - delta:
                self.pending_add_risks.append(
                    dict(**basic, risk=risk, detail={'date': date.isoformat()})
                )

    def batch_analyse_risk(self, asset, ori_account, d, batch_size=20):
        if asset is None:
            if self.pending_add_risks:
                self.perform_save_risks(self.pending_add_risks)
                self.pending_add_risks = []
            return

        basic = {'asset': asset, 'username': d['username']}
        if ori_account:
            self._analyse_item_changed(ori_account, d)
        else:
            self.pending_add_risks.append(
                dict(**basic, risk='ghost')
            )

        self._analyse_datetime_changed(ori_account, d, asset, d['username'])

        if len(self.pending_add_risks) > batch_size:
            self.batch_analyse_risk(None, None, {})

    def get_items_diff(self, ori_account, d):
        if hasattr(ori_account, '_diff'):
            return ori_account._diff

        diff = {}
        for item in self.diff_items:
            ori = getattr(ori_account, item)
            new = d.get(item, '')

            if not ori:
                continue

            if isinstance(new, timezone.datetime):
                new = ori.strftime('%Y-%m-%d %H:%M:%S')
                ori = ori.strftime('%Y-%m-%d %H:%M:%S')

            if new != ori:
                diff[item] = get_text_diff(ori, new)

        ori_account._diff = diff
        return diff

    def batch_update_gathered_account(self, ori_account, d, batch_size=20):
        if not ori_account or d is None:
            if self.pending_update_accounts:
                GatheredAccount.objects.bulk_update(self.pending_update_accounts, [*self.diff_items])
                self.pending_update_accounts = []
            return

        diff = self.get_items_diff(ori_account, d)
        if diff:
            for k in diff:
                setattr(ori_account, k, d[k])
            self.pending_update_accounts.append(ori_account)

        if len(self.pending_update_accounts) > batch_size:
            self.batch_update_gathered_account(None, None)

    def update_or_create_accounts(self):
        for asset, accounts_data in self.asset_account_info.items():
            with (tmp_to_org(asset.org_id)):
                gathered_accounts = []
                for d in accounts_data:
                    username = d['username']
                    ori_account = self.ori_gathered_accounts_mapper.get('{}_{}'.format(asset.id, username))

                    if not ori_account:
                        self.batch_create_gathered_account(d)
                    else:
                        self.batch_update_gathered_account(ori_account, d)

                    self.batch_analyse_risk(asset, ori_account, d)

                self.update_gather_accounts_status(asset)
                GatheredAccount.sync_accounts(gathered_accounts, self.is_sync_account)

        self.batch_create_gathered_account(None)
        self.batch_update_gathered_account(None, None)
        self.batch_analyse_risk(None, None, {})

    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)
        self.prefetch_origin_account_usernames()
        self.update_or_create_accounts()
        # self.send_email_if_need()

    def generate_send_users_and_change_info(self):
        recipients = self.execution.recipients
        if not self.asset_usernames_mapper or not recipients:
            return None, None

        users = User.objects.filter(id__in=recipients)
        if not users.exists():
            return users, None

        asset_ids = self.asset_usernames_mapper.keys()
        assets = Asset.objects.filter(id__in=asset_ids).prefetch_related('accounts')
        gather_accounts = GatheredAccount.objects.filter(asset_id__in=asset_ids, remote_present=True)

        asset_id_map = {str(asset.id): asset for asset in assets}
        asset_id_username = list(assets.values_list('id', 'accounts__username'))
        asset_id_username.extend(list(gather_accounts.values_list('asset_id', 'username')))

        system_asset_usernames_mapper = defaultdict(set)
        for asset_id, username in asset_id_username:
            system_asset_usernames_mapper[str(asset_id)].add(username)

        change_info = defaultdict(dict)
        for asset_id, usernames in self.asset_usernames_mapper.items():
            system_usernames = system_asset_usernames_mapper.get(asset_id)
            if not system_usernames:
                continue

            add_usernames = usernames - system_usernames
            remove_usernames = system_usernames - usernames

            if not add_usernames and not remove_usernames:
                continue

            change_info[str(asset_id_map[asset_id])] = {
                'add_usernames': add_usernames,
                'remove_usernames': remove_usernames
            }

        return users, dict(change_info)

    def send_email_if_need(self):
        users, change_info = self.generate_send_users_and_change_info()
        if not users or not change_info:
            return

        for user in users:
            GatherAccountChangeMsg(user, change_info).publish_async()
