from collections import Counter

__all__ = ['FormatAssetInfo']


class FormatAssetInfo:

    def __init__(self, tp):
        self.tp = tp

    @staticmethod
    def get_cpu_model_count(cpus):
        try:
            models = [cpus[i + 1] + " " + cpus[i + 2] for i in range(0, len(cpus), 3)]

            model_counts = Counter(models)

            result = ', '.join([f"{model} x{count}" for model, count in model_counts.items()])
        except Exception as e:
            print(f"Error processing CPU model list: {e}")
            result = ''

        return result

    @staticmethod
    def get_gpu_model_count(gpus):
        try:
            model_counts = Counter(gpus)

            result = ', '.join([f"{model} x{count}" for model, count in model_counts.items()])
        except Exception as e:
            print(f"Error processing GPU model list: {e}")
            result = ''

        return result

    def posix_format(self, info):
        cpus = self.get_cpu_model_count(info.get('cpu_model', []))
        gpus = self.get_gpu_model_count(info.get('gpu_model', []))

        info['gpu_model'] = gpus
        info['cpu_model'] = cpus
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
