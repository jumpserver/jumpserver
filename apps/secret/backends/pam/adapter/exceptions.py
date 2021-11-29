class PamError(Exception):
    def __init__(self, message=None, errors=None, method=None, url=None):
        if errors:
            message = ", ".join(errors)

        self.errors = errors
        self.method = method
        self.url = url

        super().__init__(message)

    def __str__(self):
        return "{0}, on {1} {2}".format(self.args[0], self.method, self.url)


class InvalidRequest(PamError):
    pass


class Unauthorized(PamError):
    pass


class Forbidden(PamError):
    pass


class InvalidPath(PamError):
    pass


class RateLimitExceeded(PamError):
    pass


class InternalServerError(PamError):
    pass


class PamNotInitialized(PamError):
    pass


class PamDown(PamError):
    pass


class UnexpectedError(PamError):
    pass


class BadGateway(PamError):
    pass


class ParamValidationError(PamError):
    pass
