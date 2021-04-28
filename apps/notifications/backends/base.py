

class BackendBase:
    def get_accounts_on_model_fields(self, users, field_name):
        accounts = []
        unbound_users = []
        account_user_mapper = {}

        for user in users:
            account = getattr(user, field_name, None)
            if account:
                account_user_mapper[account] = user
                accounts.append(account)
            else:
                unbound_users.append(user)
        return accounts, unbound_users, account_user_mapper
