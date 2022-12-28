from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger
from assets.const import AutomationTypes, Source
from orgs.utils import tmp_to_org
from .filter import GatherAccountsFilter
from ..base.manager import BasePlaybookManager

logger = get_logger(__name__)


class GatherAccountsManager(BasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_mapper = {}

    @classmethod
    def method_type(cls):
        return AutomationTypes.gather_accounts

    def host_callback(self, host, asset=None, **kwargs):
        super().host_callback(host, asset=asset, **kwargs)
        self.host_asset_mapper[host['name']] = asset
        return host

    def filter_success_result(self, host, result):
        result = GatherAccountsFilter(host).run(self.method_id_meta_mapper, result)
        return result

    @staticmethod
    def bulk_create_accounts(asset, result):
        account_objs = []
        account_model = asset.accounts.model
        account_usernames = set(asset.accounts.values_list('username', flat=True))
        with tmp_to_org(asset.org_id):
            accounts_dict = {}
            for username, data in result.items():
                comment = ''
                d = {'asset': asset, 'username': username, 'name': username, 'source': Source.COLLECTED}
                if data.get('date'):
                    comment += f"{_('Date last login')}: {data['date']}\n "
                if data.get('address'):
                    comment += f"{_('IP last login')}: {data['address'][:32]}"
                d['comment'] = comment
                accounts_dict[username] = d
            for username, data in accounts_dict.items():
                if username in account_usernames:
                    continue
                account_objs.append(account_model(**data))
            account_model.objects.bulk_create(account_objs)

    def on_host_success(self, host, result):
        info = result.get('debug', {}).get('res', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            result = self.filter_success_result(host, info)
            self.bulk_create_accounts(asset, result)
        else:
            logger.error("Not found info".format(host))
