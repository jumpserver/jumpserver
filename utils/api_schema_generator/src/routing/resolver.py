from .discover import Route

__all__ = ['resolve_view', 'View']


class View:

    def __init__(self, route: Route, view_func, view_class):
        self.route = route
        self.view_func = view_func
        self.view_class = view_class
    
    @property
    def is_func_based(self):
        return self.view_class is None


def resolve_view(route: Route) -> View:
    view_func = route.callback
    view_class = getattr(view_func, 'view_class', None)
    if not view_class:
        view_class = getattr(view_func, 'cls', None)
    view = View(route=route, view_func=view_func, view_class=view_class)
    return view

