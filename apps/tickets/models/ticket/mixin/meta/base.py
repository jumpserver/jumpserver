from . import apply_asset, apply_application, login_confirm

__all__ = ['ConstructDisplayFieldMixin', 'ConstructBodyMixin', 'CreatePermissionMixin']


modules = (apply_asset, apply_application, login_confirm)


construct_display_field_mixin_cls_name = 'ConstructDisplayFieldMixin'
construct_body_mixin_cls_name = 'ConstructBodyMixin'
create_permission_mixin_cls_name = 'CreatePermissionMixin'


def get_mixin_base_cls_list(base_cls_name):
    return [
        getattr(module, base_cls_name) for module in modules if hasattr(module, base_cls_name)
    ]


class ConstructDisplayFieldMixin(
    *get_mixin_base_cls_list(construct_display_field_mixin_cls_name)
):
    pass


class ConstructBodyMixin(
     *get_mixin_base_cls_list(construct_body_mixin_cls_name)
):
    pass


class CreatePermissionMixin(
    *get_mixin_base_cls_list(create_permission_mixin_cls_name)
):
    pass
