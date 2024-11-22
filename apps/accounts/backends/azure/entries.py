from ..base.entries import BaseEntry


class AzureBaseEntry(BaseEntry):
    @property
    def full_path(self):
        return self.path_spec


class AccountEntry(AzureBaseEntry):

    @property
    def path_spec(self):
        # 长度 0-127
        account_id = str(self.instance.id)[:18]
        path = f'assets-{self.instance.asset_id}-accounts-{account_id}'
        return path


class AccountTemplateEntry(AzureBaseEntry):

    @property
    def path_spec(self):
        path = f'account-templates-{self.instance.id}'
        return path


class HistoricalAccountEntry(AzureBaseEntry):

    @property
    def path_spec(self):
        path = f'accounts-{self.instance.instance.id}-histories-{self.instance.history_id}'
        return path
