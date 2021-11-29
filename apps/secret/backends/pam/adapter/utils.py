import six

from . import exceptions


def raise_for_error(method, url, status_code, message=None, errors=None):
    if status_code == 400:
        raise exceptions.InvalidRequest(message, errors=errors, method=method, url=url)
    elif status_code == 401:
        raise exceptions.Unauthorized(message, errors=errors, method=method, url=url)
    elif status_code == 403:
        raise exceptions.Forbidden(message, errors=errors, method=method, url=url)
    elif status_code == 404:
        raise exceptions.InvalidPath(message, errors=errors, method=method, url=url)
    elif status_code == 429:
        raise exceptions.RateLimitExceeded(
            message, errors=errors, method=method, url=url
        )
    elif status_code == 500:
        raise exceptions.InternalServerError(
            message, errors=errors, method=method, url=url
        )
    elif status_code == 501:
        raise exceptions.PamNotInitialized(
            message, errors=errors, method=method, url=url
        )
    elif status_code == 502:
        raise exceptions.BadGateway(message, errors=errors, method=method, url=url)
    elif status_code == 503:
        raise exceptions.PamDown(message, errors=errors, method=method, url=url)
    else:
        raise exceptions.UnexpectedError(message or errors, method=method, url=url)


def remove_nones(params):
    return {key: value for key, value in params.items() if value is not None}


def format_url(format_str, *args, **kwargs):
    def url_quote(maybe_str):
        # Special care must be taken for Python 2 where Unicode characters will break urllib quoting.
        # To work around this, we always cast to a Unicode type, then UTF-8 encode it.
        # Doing this is version agnostic and returns the same result in Python 2 or 3.
        unicode_str = six.text_type(maybe_str)
        utf8_str = unicode_str.encode("utf-8")
        return six.moves.urllib.parse.quote(utf8_str)

    escaped_args = [url_quote(value) for value in args]
    escaped_kwargs = {key: url_quote(value) for key, value in kwargs.items()}

    return format_str.format(*escaped_args, **escaped_kwargs)
