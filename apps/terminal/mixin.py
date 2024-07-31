from terminal.utils.loki_client import get_loki_client

__all__ = ['LokiMixin', ]


class LokiMixin:

    @staticmethod
    def get_loki_client():
        return get_loki_client()

    @staticmethod
    def create_loki_query(components, search):
        stream_selector = '{component!=""}'
        if components:
            stream_selector = '{component=~"%s"}' % components
        query = f'{stream_selector} |="{search}"'
        return query
