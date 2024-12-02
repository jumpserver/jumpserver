from django.utils import timezone
from datetime import datetime

__all__ = ['GatherAccountsFilter']


def parse_date(date_str, default=''):
    if not date_str:
        return default
    if date_str == 'Never':
        return None
    try:
        dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M:%S')
        return timezone.make_aware(dt, timezone.get_current_timezone())
    except ValueError:
        return default


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

        last_login = info.pop('last_login', '')
        user_last_login = {}
        for line in last_login:
            if not line.strip() or ' ' not in line:
                continue
            username, login = line.split(' ', 1)
            user_last_login[username] = login.split()

        user_authorized = info.pop('user_authorized', [])
        username_authorized = {}
        for line in user_authorized:
            if ':' not in line:
                continue
            username, authorized = line.split(':', 1)
            username_authorized[username.strip()] = authorized.strip()

        passwd_date = info.pop('passwd_date', [])
        username_password_date = {}
        for line in passwd_date:
            if ':' not in line:
                continue
            username, password_date = line.split(':', 1)
            username_password_date[username.strip()] = password_date.strip().split()

        result = {}
        users = info.pop('users', '')

        for username in users:
            if not username:
                continue
            user = dict()

            login = user_last_login.get(username) or ''
            if login and len(login) == 3:
                user['address_last_login'] = login[0][:32]
                try:
                    login_date = timezone.datetime.fromisoformat(login[1])
                    user['date_last_login'] = login_date
                except ValueError:
                    pass

            start_date = timezone.make_aware(timezone.datetime(1970, 1, 1))
            _password_date = username_password_date.get(username) or ''
            if _password_date and len(_password_date) == 2:
                if _password_date[0] and _password_date[0] != '0':
                    user['date_password_change'] = start_date + timezone.timedelta(days=int(_password_date[0]))
                if _password_date[1] and _password_date[1] != '0':
                    user['date_password_expired'] = start_date + timezone.timedelta(days=int(_password_date[1]))

            user['groups'] = username_groups.get(username) or ''
            user['sudoers'] = username_sudo.get(username) or ''
            user['authorized_keys'] = username_authorized.get(username) or ''
            result[username] = user
        return result

    @staticmethod
    def windows_filter(info):
        result = {}
        for user_details in info['user_details']:
            user_info = {}
            lines = user_details['stdout_lines']
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split('  ', 1)
                if len(parts) == 2:
                    key, value = parts
                    user_info[key.strip()] = value.strip()
            user = {
                'username': user_info.get('User name', ''),
                'groups': user_info.get('Global Group memberships', ''),
                'date_password_change': parse_date(user_info.get('Password last set', '')),
                'date_password_expired': parse_date(user_info.get('Password expires', '')),
                'date_last_login': parse_date(user_info.get('Last logon', '')),
                'can_change_password': user_info.get('User may change password', 'Yes')
            }
            result[user['username']] = user
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
