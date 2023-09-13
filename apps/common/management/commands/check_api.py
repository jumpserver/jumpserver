import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import URLPattern, URLResolver

from jumpserver.urls import api_v1

path_uuid_pattern = re.compile(r'<\w+:\w+>', re.IGNORECASE)
uuid_pattern = re.compile(r'\(\(\?P<.*>[^)]+\)/\)\?', re.IGNORECASE)
uuid2_pattern = re.compile(r'\(\?P<.*>\[\/\.\]\+\)', re.IGNORECASE)
uuid3_pattern = re.compile(r'\(\?P<.*>\[/\.]\+\)')


def list_urls(patterns, path=None):
    """ recursive """
    if not path:
        path = []
    result = []
    for pattern in patterns:
        if isinstance(pattern, URLPattern):
            result.append(''.join(path) + str(pattern.pattern))
        elif isinstance(pattern, URLResolver):
            result += list_urls(pattern.url_patterns, path + [str(pattern.pattern)])
    return result


def parse_to_url(url):
    uid = '00000000-0000-0000-0000-000000000000'

    url = url.replace('^', '')
    url = url.replace('?$', '')
    url = url.replace('(?P<format>[a-z0-9]+)', '')
    url = url.replace('((?P<terminal>[/.]{36})/)?', uid + '/')
    url = url.replace('(?P<pk>[/.]+)', uid)
    url = url.replace('\.', '')
    url = url.replace('//', '/')
    url = url.strip('$')
    url = re.sub(path_uuid_pattern, uid, url)
    url = re.sub(uuid2_pattern, uid, url)
    url = re.sub(uuid_pattern, uid + '/', url)
    url = re.sub(uuid3_pattern, uid, url)
    url = url.replace('(00000000-0000-0000-0000-000000000000/)?', uid + '/')
    return url


def get_api_urls():
    urls = []
    api_urls = list_urls(api_v1)
    for ourl in api_urls:
        url = parse_to_url(ourl)
        if 'render-to-json' in url:
            continue
        url = '/api/v1/' + url
        urls.append((url, ourl))
    return set(urls)


known_unauth_urls = [
    "/api/v1/authentication/passkeys/auth/",
    "/api/v1/prometheus/metrics/",
    "/api/v1/authentication/auth/",
    "/api/v1/settings/logo/",
    "/api/v1/settings/public/open/",
    "/api/v1/authentication/passkeys/login/",
    "/api/v1/authentication/tokens/",
    "/api/v1/authentication/mfa/challenge/",
    "/api/v1/authentication/password/reset-code/",
    "/api/v1/authentication/login-confirm-ticket/status/",
    "/api/v1/authentication/mfa/select/",
    "/api/v1/authentication/mfa/send-code/",
    "/api/v1/authentication/sso/login/"
]

known_error_urls = [
    '/api/v1/terminal/terminals/00000000-0000-0000-0000-000000000000/sessions/00000000-0000-0000-0000-000000000000/replay/download/',
    '/api/v1/terminal/sessions/00000000-0000-0000-0000-000000000000/replay/download/',
]

errors = {}


class Command(BaseCommand):
    help = 'Check api if unauthorized'

    def handle(self, *args, **options):
        settings.LOG_LEVEL = 'ERROR'
        urls = get_api_urls()
        client = Client()
        unauth_urls = []
        error_urls = []
        unformat_urls = []

        for url, ourl in urls:
            if '(' in url or '<' in url:
                unformat_urls.append([url, ourl])
                continue

            try:
                response = client.get(url, follow=True)
                if response.status_code != 401:
                    errors[url] = str(response.status_code) + ' ' + str(ourl)
                    unauth_urls.append(url)
            except Exception as e:
                errors[url] = str(e)
                error_urls.append(url)

        unauth_urls = set(unauth_urls) - set(known_unauth_urls)
        print("\nUnauthorized urls:")
        if not unauth_urls:
            print("  Empty, very good!")
        for url in unauth_urls:
            print('"{}", {}'.format(url, errors.get(url, '')))

        print("\nError urls:")
        if not error_urls:
            print("  Empty, very good!")
        for url in set(error_urls):
            print(url, ': ' + errors.get(url))

        print("\nUnformat urls:")
        if not unformat_urls:
            print("  Empty, very good!")
        for url in unformat_urls:
            print(url)
