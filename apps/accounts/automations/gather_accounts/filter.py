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
            for username, data in user_dict.items():
                if data.get('account_locked') == 'N':
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
        result = {}
        for line in info:
            data = line.split('@')
            if len(data) == 1:
                result[line] = {}
                continue

            if len(data) != 3:
                continue
            username, address, dt = data
            date = timezone.datetime.strptime(f'{dt} +0800', '%b %d %H:%M:%S %Y %z')
            result[username] = {'address': address, 'date': date}
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
