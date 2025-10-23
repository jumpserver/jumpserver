from http.cookies import SimpleCookie

from asgiref.sync import sync_to_async

from orgs.utils import tmp_to_org


class OrgMixin:
    cookie = None
    org = None

    def get_cookie(self):
        try:
            headers = self.scope['headers']
            headers_dict = {key.decode('utf-8'): value.decode('utf-8') for key, value in headers}
            cookie = SimpleCookie(headers_dict.get('cookie', ''))
        except Exception as e:
            cookie = SimpleCookie()
        return cookie

    def get_current_org(self):
        oid = self.cookie.get('X-JMS-ORG')
        return oid.value if oid else None

    @sync_to_async
    def has_perms(self, user, perms):
        self.cookie = self.get_cookie()
        self.org = self.get_current_org()
        with tmp_to_org(self.org):
            return user.has_perms(perms)
