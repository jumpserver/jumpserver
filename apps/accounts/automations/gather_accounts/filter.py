import re

from django.utils import timezone

__all__ = ['GatherAccountsFilter']


# TODO 后期会挪到playbook中
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
        username_pattern = re.compile(r'^(\S+)')
        ip_pattern = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        login_time_pattern = re.compile(r'\w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}')
        result = {}
        for line in info:
            usernames = username_pattern.findall(line)
            username = ''.join(usernames)
            if username:
                result[username] = {}
            else:
                continue
            ip_addrs = ip_pattern.findall(line)
            ip_addr = ''.join(ip_addrs)
            if ip_addr:
                result[username].update({'address': ip_addr})
            login_times = login_time_pattern.findall(line)
            if login_times:
                date = timezone.datetime.strptime(f'{login_times[0]} +0800', '%b %d %H:%M:%S %Y %z')
                result[username].update({'date': date})
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
