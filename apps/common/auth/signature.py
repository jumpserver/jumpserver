from rest_framework import authentication
from rest_framework import exceptions

from httpsig import HeaderVerifier, utils

"""
Reusing failure exceptions serves several purposes:

    1. Lack of useful information regarding the failure inhibits attackers
    from learning about valid keyIDs or other forms of information leakage.
    Using the same actual object for any failure makes preventing such
    leakage through mistakenly-distinct error messages less likely.

    2. In an API scenario, the object is created once and raised many times
    rather than generated on every failure, which could lead to higher loads
    or memory usage in high-volume attack scenarios.

"""
FAILED = exceptions.AuthenticationFailed('Invalid signature.')
IP_NOT_ALLOW = exceptions.AuthenticationFailed('Ip is not in access ip list.')


class SignatureAuthentication(authentication.BaseAuthentication):
    """
    DRF authentication class for HTTP Signature support.

    You must subclass this class in your own project and implement the
    `fetch_user_data(self, keyId, algorithm)` method, returning a tuple of
    the User object and a bytes object containing the user's secret. Note
    that key_id and algorithm are DIRTY as they are supplied by the client
    and so must be verified in your subclass!

    You may set the following class properties in your subclass to configure
    authentication for your particular use case:

    :param www_authenticate_realm:  Default: "api"
    :param required_headers:        Default: ["(request-target)", "date"]
    """

    www_authenticate_realm = "api"
    required_headers = ["(request-target)", "date"]

    def fetch_user_data(self, key_id, algorithm=None):
        """Returns a tuple (User, secret) or (None, None)."""
        raise NotImplementedError()

    def is_ip_allow(self, key_id, request):
        raise NotImplementedError()

    def authenticate_header(self, request):
        """
        DRF sends this for unauthenticated responses if we're the primary
        authenticator.
        """
        h = " ".join(self.required_headers)
        return 'Signature realm="%s",headers="%s"' % (
            self.www_authenticate_realm, h)

    def authenticate(self, request):
        """
        Perform the actual authentication.

        Note that the exception raised is always the same. This is so that we
        don't leak information about in/valid keyIds and other such useful
        things.
        """
        auth_header = authentication.get_authorization_header(request)
        if not auth_header or len(auth_header) == 0:
            return None

        method, fields = utils.parse_authorization_header(auth_header)

        # Ignore foreign Authorization headers.
        if method.lower() != 'signature':
            return None

        # Verify basic header structure.
        if len(fields) == 0:
            raise FAILED

        # Ensure all required fields were included.
        if len({"keyid", "algorithm", "signature"} - set(fields.keys())) > 0:
            raise FAILED

        key_id = fields["keyid"]
        # Fetch the secret associated with the keyid
        user, secret = self.fetch_user_data(
            key_id,
            algorithm=fields["algorithm"]
        )

        if not (user and secret):
            raise FAILED

        if not self.is_ip_allow(key_id, request):
            raise IP_NOT_ALLOW

        # Gather all request headers and translate them as stated in the Django docs:
        # https://docs.djangoproject.com/en/1.6/ref/request-response/#django.http.HttpRequest.META
        headers = {}
        for key in request.META.keys():
            if key.startswith("HTTP_") or \
                    key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header = key[5:].lower().replace('_', '-')
                headers[header] = request.META[key]

        # Verify headers
        hs = HeaderVerifier(
            headers,
            secret,
            required_headers=self.required_headers,
            method=request.method.lower(),
            path=request.get_full_path()
        )

        # All of that just to get to this.
        if not hs.verify():
            raise FAILED

        return user, fields["keyid"]
