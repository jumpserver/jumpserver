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
        queryset = self.label_assets(queryset)
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

    def label_assets(self, queryset):
        from assets.models import Label
        query_keys = self.request.query_params.keys()
        all_label_keys = Label.objects.values_list('name', flat=True)
        valid_keys = set(all_label_keys) & set(query_keys)
        labels_query = {}
        for key in valid_keys:
            labels_query[key] = self.request.query_params.get(key)

        queryset = self.filter_labels_queryset(queryset, labels_query)
        return queryset

    def filter_labels_queryset(self, queryset, labels_query):
        filter_queryset = []
        if not labels_query:
            return queryset
        for item in queryset:
            if item.labels.filter(name__in=labels_query.keys()) and \
                    item.labels.filter(value__in=labels_query.values()):
                filter_queryset.append(item)
        return filter_queryset


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
