import re
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import URLPattern, URLResolver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

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
    url = url.replace('(?P<label>.*)', uid)
    url = url.replace('(?P<res_type>.*)', '1')
    url = url.replace('(?P<name>[\\w.@]+)', '')
    url = url.replace('<str:name>', 'zh-hans')
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
    "/api/v1/authentication/face/context/",
    "/api/v1/authentication/mfa/send-code/",
    "/api/v1/authentication/sso/login/",
    "/api/v1/authentication/user-session/",
    "/api/v1/settings/i18n/zh-hans/"
]

known_error_urls = [
    '/api/v1/terminal/terminals/00000000-0000-0000-0000-000000000000/sessions/00000000-0000-0000-0000-000000000000/replay/download/',
    '/api/v1/terminal/sessions/00000000-0000-0000-0000-000000000000/replay/download/',
]

# API 白名单 - 普通用户可以访问的 API
user_accessible_urls = [
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
    "/api/v1/authentication/face/context/",
    "/api/v1/authentication/mfa/send-code/",
    "/api/v1/authentication/sso/login/",
    "/api/v1/authentication/user-session/",
    "/api/v1/settings/i18n/zh-hans/",
    # 添加更多普通用户可以访问的 API
    "/api/v1/users/profile/",
    "/api/v1/users/change-password/",
    "/api/v1/users/logout/",
]

errors = {}


class Command(BaseCommand):
    """
    Check API authorization and user access permissions.
    
    This command performs two types of checks:
    1. Anonymous access check - finds APIs that can be accessed without authentication
    2. User access check - finds APIs that can be accessed by a normal user
    
    The functionality is split into two methods:
    - check_anonymous_access(): Checks for APIs accessible without authentication
    - check_user_access(): Checks for APIs accessible by a normal user
    
    Usage examples:
        # Check both anonymous and user access (default behavior)
        python manage.py check_api
        
        # Check only anonymous access
        python manage.py check_api --skip-user-check
        
        # Check only user access
        python manage.py check_api --skip-anonymous-check
        
        # Check user access and update whitelist
        python manage.py check_api --update-whitelist
    """
    help = 'Check API authorization and user access permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-anonymous-check',
            action='store_true',
            help='Skip anonymous access check (only check user access)',
        )
        parser.add_argument(
            '--skip-user-check',
            action='store_true',
            help='Skip user access check (only check anonymous access)',
        )
        parser.add_argument(
            '--update-whitelist',
            action='store_true',
            help='Update the user accessible URLs whitelist based on current scan results',
        )

    def create_test_user(self):
        """创建测试用户"""
        User = get_user_model()
        username = 'test_user_api_check'
        email = 'test@example.com'
        
        # 删除可能存在的测试用户
        User.objects.filter(username=username).delete()
        password = uuid.uuid4().hex
        
        # 创建新的测试用户
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )
        return user

    def check_user_api_access(self, urls):
        """检查普通用户可以访问的 API"""
        user = self.create_test_user()
        client = Client()
        client.defaults['HTTP_HOST'] = 'localhost'
        
        # 登录用户
        login_success = client.login(username=user.username, password='test_password_123')
        if not login_success:
            self.stdout.write(
                self.style.ERROR('Failed to login test user')
            )
            return [], []
        
        accessible_urls = []
        error_urls = []
        
        self.stdout.write('Checking user API access...')
        
        for url, ourl in urls:
            if '(' in url or '<' in url:
                continue
                
            try:
                response = client.get(url, follow=True)
                # 如果状态码是 200 或 201，说明用户可以访问
                if response.status_code in [200, 201]:
                    accessible_urls.append((url, ourl, response.status_code))
                elif response.status_code == 403:
                    # 403 表示权限不足，这是正常的
                    pass
                else:
                    # 其他状态码可能是错误
                    error_urls.append((url, ourl, response.status_code))
            except Exception as e:
                error_urls.append((url, ourl, str(e)))
        
        # 清理测试用户
        user.delete()
        
        return accessible_urls, error_urls

    def check_anonymous_access(self, urls):
        """检查匿名访问权限"""
        client = Client()
        client.defaults['HTTP_HOST'] = 'localhost'
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
        print("\n=== Anonymous Access Check ===")
        print("Unauthorized urls:")
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

    def check_user_access(self, urls, update_whitelist=False):
        """检查用户访问权限"""
        print("\n=== User Access Check ===")
        accessible_urls, user_error_urls = self.check_user_api_access(urls)
        
        # print(f"\nFound {len(accessible_urls)} accessible URLs for normal user:")
        # for url, ourl, status_code in accessible_urls:
        #     print(f'  "{url}" (status: {status_code}) - {ourl}')
        
        # if user_error_urls:
        #     print(f"\nUser access errors ({len(user_error_urls)}):")
        #     for url, ourl, error in user_error_urls:
        #         print(f'  "{url}" - {error}')
        
        # 检查是否有不在白名单中的可访问 API
        accessible_url_list = [url for url, _, _ in accessible_urls]
        unexpected_access = set(accessible_url_list) - set(user_accessible_urls)
        
        if unexpected_access:
            print(f"\n⚠️  WARNING: Found {len(unexpected_access)} URLs accessible by user but not in whitelist:")
            for url in unexpected_access:
                print(f'  "{url}"')
            print("\nConsider adding these URLs to user_accessible_urls whitelist.")
        else:
            print("\n✅ All accessible URLs are in the whitelist.")
        
        # 如果启用了更新白名单选项
        if update_whitelist:
            print("\n=== Updating Whitelist ===")
            new_whitelist = sorted(set(user_accessible_urls + accessible_url_list))
            print("Updated whitelist would include:")
            for url in new_whitelist:
                print(f'    "{url}",')
            print(f"\nTotal URLs in whitelist: {len(new_whitelist)}")

    def handle(self, *args, **options):
        settings.LOG_LEVEL = 'ERROR'
        urls = get_api_urls()
        
        # 检查匿名访问权限（默认执行）
        if not options['skip_anonymous_check']:
            self.check_anonymous_access(urls)
        
        # 检查用户访问权限（默认执行）
        if not options['skip_user_check']:
            self.check_user_access(urls, options['update_whitelist'])
