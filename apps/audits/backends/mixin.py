from perms.const import ActionChoices


class OperateStorageMixin(object):
    @staticmethod
    def _get_special_handler(resource_type):
        # 根据资源类型，处理特殊字段
        resource_map = {
            'Asset permission': lambda k, v: ActionChoices.display(int(v)) if k == 'Actions' else v
        }
        return resource_map.get(resource_type, lambda k, v: v)
