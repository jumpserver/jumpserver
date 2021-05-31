from django.conf import settings


class BackendBase:
    # User 表中的字段
    account_field = None

    # Django setting 中的字段名
    is_enable_field_in_settings = None

    def get_accounts(self, users):
        accounts = []
        unbound_users = []
        account_user_mapper = {}

        for user in users:
            account = getattr(user, self.account_field, None)
            if account:
                account_user_mapper[account] = user
                accounts.append(account)
            else:
                unbound_users.append(user)
        return accounts, unbound_users, account_user_mapper

    @classmethod
    def get_account(cls, user):
        return getattr(user, cls.account_field)

    @classmethod
    def is_enable(cls):
        enable = getattr(settings, cls.is_enable_field_in_settings)
        return bool(enable)
