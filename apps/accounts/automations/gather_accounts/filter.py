from django.utils import timezone

__all__ = ['GatherAccountsFilter']


# TODO 后期会挪到 playbook 中
class GatherAccountsFilter:
    def __init__(self, tp):
        self.tp = tp

    @staticmethod
    def mysql_filter(info):
        result = {}
        for _, user_dict in info.items():
            for username, _ in user_dict.items():
                if len(username.split('.')) == 1:
                    result[username] = {}
        return result

    @staticmethod
    def postgresql_filter(info):
        result = {}
        for username in info:
            result[username] = {}
        return result

    @staticmethod
    def posix_filter(info):
        user_groups = info.pop('user_groups', [])
        username_groups = {}
        for line in user_groups:
            if ':' not in line:
                continue
            username, groups = line.split(':', 1)
            username_groups[username.strip()] = groups.strip()

        user_sudo = info.pop('user_sudo', [])
        username_sudo = {}
        for line in user_sudo:
            if ':' not in line:
                continue
            username, sudo = line.split(':', 1)
            if not sudo.strip():
                continue
            username_sudo[username.strip()] = sudo.strip()

        user_authorized = info.pop('user_authorized', [])
        username_authorized = {}
        for line in user_authorized:
            if ':' not in line:
                continue
            username, authorized = line.split(':', 1)
            username_authorized[username.strip()] = authorized.strip()

        result = {}
        users = info.pop('users', '')
        for line in users:
            parts = line.split()
            if len(parts) < 4:
                continue

            username = parts[0]
            if not username:
                continue
            user = dict()
            address = parts[2]
            user['address_last_login'] = address
            login_time = parts[3]

            try:
                login_date = timezone.datetime.fromisoformat(login_time)
                user['date_last_login'] = login_date
            except ValueError:
                pass

            user['groups'] = username_groups.get(username) or ''
            user['sudoers'] = username_sudo.get(username) or ''
            user['authorized_keys'] = username_authorized.get(username) or ''

            result[username] = user
        return result

    @staticmethod
    def windows_filter(info):
        info = info[4:-2]
        result = {}
        for i in info:
            for username in i.split():
                result[username] = {}
        return result

    def run(self, method_id_meta_mapper, info):
        run_method_name = None
        for k, v in method_id_meta_mapper.items():
            if self.tp not in v['type']:
                continue
            run_method_name = k.replace(f'{v["method"]}_', '')

        if not run_method_name:
            return info

        if hasattr(self, f'{run_method_name}_filter'):
            return getattr(self, f'{run_method_name}_filter')(info)
        return info
