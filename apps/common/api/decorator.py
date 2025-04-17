from common.utils import get_logger


logger = get_logger(__file__)


def deprecated_api(replacement=None, sunset_date=None):
    """类视图废弃装饰器"""
    def decorator(cls):
        original_dispatch = cls.dispatch

        def new_dispatch(self, request, *args, **kwargs):
            logger.warning(
                f'The client {request.get_host()} calls the deprecated interface: {request.path}'
            )
            response = original_dispatch(self, request, *args, **kwargs)
            response.headers["Deprecation"] = "true"
            if replacement:
                response.headers["Link"] = f'<{replacement}>; rel="deprecation"'
            if sunset_date:
                response.headers["Sunset"] = sunset_date
            if hasattr(response, "data") and isinstance(response.data, dict):
                response.data.update({
                    'warning': f'This interface has been deprecated. Please use {replacement} instead.'
                })
            return response

        cls.dispatch = new_dispatch
        return cls
    return decorator
