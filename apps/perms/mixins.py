# ~*~ coding: utf-8 ~*~
#

from orgs.utils import set_to_root_org

__all__ = [
    'AssetsFilterMixin', 'RemoteAppFilterMixin', 'ChangeOrgIfNeedMixin',
]


class AssetsFilterMixin(object):
    """
    对资产进行过滤(查询，排序)
    """

    def filter_queryset(self, queryset):
        queryset = self.search_assets(queryset)
        queryset = self.filter_labels(queryset)
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

    def filter_labels(self, queryset):
        from assets.models import Label
        query_keys = self.request.query_params.keys()
        all_label_keys = Label.objects.values_list('name', flat=True)
        valid_keys = set(all_label_keys) & set(query_keys)
        labels_query = {}
        for key in valid_keys:
            labels_query[key] = self.request.query_params.get(key)
        if not labels_query:
            return queryset

        labels = set()
        for k, v in labels_query.items():
            label = Label.objects.filter(name=k, value=v).first()
            if not label:
                continue
            labels.add(label)

        _queryset = []
        for asset in queryset:
            _labels = set(asset.labels.all()) & set(labels)
            if _labels and len(_labels) == len(set(labels)):
                _queryset.append(asset)
        return _queryset


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


class ChangeOrgIfNeedMixin(object):

    @staticmethod
    def change_org_if_need(request, kwargs):
        if request.user.is_authenticated and request.user.is_superuser \
                or request.user.is_app \
                or kwargs.get('pk') is None:
            set_to_root_org()

    def get(self, request, *args, **kwargs):
        self.change_org_if_need(request, kwargs)
        return super().get(request, *args, **kwargs)
