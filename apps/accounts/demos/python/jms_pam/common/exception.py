class JumpServerPAMSDKException(Exception):
    def __init__(
        self, code, message, status_code=None, detail=None,
        request_id=None, original_error=None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.request_id = request_id
        self.original_error = original_error
        super().__init__(f'[{code}] {detail or message}')


REVOKED_CODES = frozenset((
    'credential_not_found', 'credential_not_selected', 'credential_not_authorized',
))


def response_error_code(error):
    return (
        getattr(error, 'code', '')
        if getattr(error, 'status_code', None) in (400, 403, 404) else ''
    )


def identity_denied(error):
    status_code = getattr(error, 'status_code', None)
    return status_code == 401 or (
        status_code == 403 and getattr(error, 'code', '') not in REVOKED_CODES
    )
