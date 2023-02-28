__all__ = ['FormatAssetInfo']


class FormatAssetInfo:

    def __init__(self, tp):
        self.tp = tp

    @staticmethod
    def posix_format(info):
        for cpu_model in info.get('cpu_model', []):
            if cpu_model.endswith('GHz') or cpu_model.startswith("Intel"):
                break
        else:
            cpu_model = ''
        info['cpu_model'] = cpu_model[:48]
        info['cpu_count'] = info.get('cpu_count', 0)
        return info

    def run(self, method_id_meta_mapper, info):
        for k, v in info.items():
            info[k] = v.strip() if isinstance(v, str) else v

        run_method_name = None
        for k, v in method_id_meta_mapper.items():
            if self.tp not in v['type']:
                continue
            run_method_name = k.replace(f'{v["method"]}_', '')

        if not run_method_name:
            return info

        if hasattr(self, f'{run_method_name}_format'):
            return getattr(self, f'{run_method_name}_format')(info)
        return info
