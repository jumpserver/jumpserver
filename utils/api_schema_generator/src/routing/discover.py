from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver


__all__ = ['discover_routes']


class Route:

    def __init__(self, url_pattern: URLPattern, path_prefix):
        self.url_pattern = url_pattern
        self.path = f'{path_prefix}{url_pattern.pattern}'
        self.callback = url_pattern.callback
    

def extract_url_patterns(patterns, path_prefix='/'):
    routes = []
    for p in patterns:
        if isinstance(p, URLResolver):
            _path_prefix = f'{path_prefix}{p.pattern}'
            _routes = extract_url_patterns(p.url_patterns, path_prefix=_path_prefix)
            routes.extend(_routes)
        elif isinstance(p, URLPattern):
            route = Route(url_pattern=p, path_prefix=path_prefix)
            routes.append(route)
        else:
            print(f'Skip: unknown pattern type: {type(p)}')
    return routes


def discover_routes():
    resolver = get_resolver()
    routes = extract_url_patterns(resolver.url_patterns)
    return routes
