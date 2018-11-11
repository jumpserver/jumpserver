# ~*~ coding: utf-8 ~*~
#


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
