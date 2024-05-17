from terminal.utils.loki_client import get_loki_client

__all__ = ['LokiMixin', ]

class LokiMixin:

    def get_loki_client(self):
        return get_loki_client()

    def create_loki_query(self, components, search):
        stream_selector = '{component!=""}'
        if components:
            stream_selector = '{component=~"%s"}' % components
        query = f'{stream_selector} |="{search}"'
        return query
