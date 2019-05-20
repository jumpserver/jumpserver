# ~*~ coding: utf-8 ~*~
#


__all__ = [
    'AssetsFilterMixin', 'RemoteAppFilterMixin',
]


class AssetsFilterMixin(object):
    """
    对资产进行过滤(查询，排序)
    """

    def filter_queryset(self, queryset):
        queryset = self.search_assets(queryset)
        queryset = self.sort_assets(queryset)
        return queryset

    def search_assets(self, queryset):
        from perms.utils import is_obj_attr_has
        value = self.request.query_params.get('search')
        if not value:
            return queryset
        queryset = [asset for asset in queryset if is_obj_attr_has(asset, value)]
        return queryset

    def sort_assets(self, queryset):
        from perms.utils import sort_assets
        order_by = self.request.query_params.get('order')
        if not order_by:
            order_by = 'hostname'

        if order_by.startswith('-'):
            order_by = order_by.lstrip('-')
            reverse = True
        else:
            reverse = False

        queryset = sort_assets(queryset, order_by=order_by, reverse=reverse)
        return queryset


class RemoteAppFilterMixin(object):
    """
    对RemoteApp进行过滤(查询，排序)
    """

    def filter_queryset(self, queryset):
        queryset = self.search_remote_apps(queryset)
        queryset = self.sort_remote_apps(queryset)
        return queryset

    def search_remote_apps(self, queryset):
        value = self.request.query_params.get('search')
        if not value:
            return queryset
        queryset = [
            remote_app for remote_app in queryset if value in remote_app.name
        ]
        return queryset

    def sort_remote_apps(self, queryset):
        order_by = self.request.query_params.get('order')
        if not order_by:
            order_by = 'name'
        if order_by.startswith('-'):
            order_by = order_by.lstrip('-')
            reverse = True
        else:
            reverse = False

        queryset = sorted(
            queryset, key=lambda x: getattr(x, order_by), reverse=reverse
        )
        return queryset
