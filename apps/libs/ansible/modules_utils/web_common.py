import time

from urllib.parse import urlparse, urljoin

from playwright.sync_api import sync_playwright, TimeoutError
from ansible.module_utils._text import to_native


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_user=dict(type='str', required=False),
        login_password=dict(type='str', required=False, no_log=True),
        steps=dict(type='list', required=False, default=[]),
        load_state=dict(type='str', required=False, default='load'),
        timeout=dict(type='int', required=False, default=10000),
    )
    return options


class WebAutomationHandler(object):
    def __init__(self, address, load_state=None, timeout=10000, extra_infos=None):
        self._response_mapping = {}
        self._context = None
        self._extra_infos = extra_infos or {}

        self.address = address
        self.load_state = load_state or 'load'
        self.timeout = timeout

    def _iframe(self, selector):
        if not selector:
            return

        if selector.startswith(('id=', 'name=')):
            key, value = selector.split('=', 1)
            frame = self._context.frame(name=value)
        else:
            iframe_elem = self._context.wait_for_selector(selector, timeout=self.timeout)
            frame = iframe_elem.content_frame()

        if not frame:
            raise RuntimeError(f"Iframe not found: {selector}")
        frame.wait_for_selector("body", timeout=self.timeout)
        self._context = frame

    def _input(self, selector, value):
        if not selector:
            return

        elem = self._context.wait_for_selector(selector, timeout=self.timeout)
        elem.fill(value)

    def _click(self, selector):
        if not selector:
            return

        elem = self._context.wait_for_selector(selector, timeout=self.timeout)
        elem.scroll_into_view_if_needed()
        elem.click(timeout=self.timeout)

    def __combine_url(self, url_path):
        if not url_path:
            return self.address

        parsed = urlparse(url_path)
        if parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        else:
            re_parsed = urlparse(urljoin(self.address, url_path))
            return f"{re_parsed.scheme}://{re_parsed.netloc}{re_parsed.path}"

    def _check(self, config: dict):
        method = config.get('type')
        if not method:
            return

        if method == 'wait_for_url':
            url = config.get('url', '')
            url = self.__combine_url(url)
            self._context.wait_for_url(url, timeout=self.timeout)
        elif method == 'wait_for_selector':
            selector = config.get('selector', '')
            self._context.wait_for_selector(selector, timeout=self.timeout)
        elif method == 'check_response':
            self._check_response(
                method=config.get('method'),
                url=config.get('url'),
                status_code=config.get('status_code'),
                body_expr=config.get('body_expr'),
            )

    @staticmethod
    def __get_nested_value(data, key_path):
        keys = key_path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                index = int(key)
                current = current[index] if 0 <= index < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current

    @staticmethod
    def __compare_values(actual, expected):
        if actual is None:
            return expected.lower() in ['none', 'null', '']

        if isinstance(actual, str):
            return str(actual) == str(expected)

        if isinstance(actual, (int, float)):
            try:
                return float(actual) == float(expected)
            except ValueError:
                return str(actual) == str(expected)

        if isinstance(actual, bool):
            expected_lower = expected.lower()
            if expected_lower in ['true', '1', 'yes']:
                return actual is True
            elif expected_lower in ['false', '0', 'no']:
                return actual is False

        if isinstance(actual, list) and expected.startswith('length='):
            expected_len = int(expected[7:])
            return len(actual) == expected_len

        return str(actual) == str(expected)

    def __validate_response(self, resp_data, body_expr):
        try:
            if '=' in body_expr:
                key, expected_value = body_expr.split('=', 1)
            elif ':' in body_expr:
                key, expected_value = body_expr.split(':', 1)
            else:
                return False

            key = key.strip()
            expected_value = expected_value.strip()
            actual_value = self.__get_nested_value(resp_data, key)
            return self.__compare_values(actual_value, expected_value)
        except Exception:  # noqa
            return False

    def _check_response(self, method, url, status_code, body_expr):
        if not method:
            return False

        timeout_seconds = self.timeout / 1000
        start_time = time.time()
        check_url = self.__combine_url(url)
        expected_status = None
        if status_code:
            try:
                expected_status = int(status_code)
            except ValueError:
                expected_status = None

        while time.time() - start_time < timeout_seconds:
            self._context.wait_for_timeout(50)
            method = method.upper()

            if method not in self._response_mapping:
                continue

            url_mapping = self._response_mapping[method]
            if len(url_mapping) == 0:
                continue

            url, response = url_mapping.popitem()
            if expected_status and response['status'] != expected_status:
                continue

            if check_url and url != check_url:
                continue

            if body_expr and not self.__validate_response(response['data'], body_expr):
                continue
            return

        raise TimeoutError(
            f'Check response failed: method={method}, url={url}, status={status_code}'
        )

    def _handle_response(self, response):
        if response.url.endswith(('.js', '.css')):
            return

        method = response.request.method.upper()
        url = self.__combine_url(response.url)
        self._response_mapping.setdefault(method, {})

        try:
            data = response.json()
        except Exception:  # noqa
            data = {}
        response_data = {'status': response.status, 'data': data}
        self._response_mapping[method][url] = response_data

    def execute(self, steps: list):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            self._context = browser.new_page()

            try:
                self._context.on('response', self._handle_response)
                self._context.goto(self.address, wait_until=self.load_state)

                for step in steps:
                    action_type = step.get('action')
                    if not action_type:
                        continue

                    config = step.get('config', {})
                    if action_type == 'iframe':
                        self._iframe(config['selector'])
                    elif action_type == 'input':
                        value = self._extra_infos.get(config['value'], config['value'])
                        self._input(config['selector'], value)
                    elif action_type == 'click':
                        self._click(config['selector'])
                    elif action_type == 'check':
                        self._check(config)
                    elif action_type == 'sleep':
                        try:
                            sleep_time = float(config['value'])
                        except ValueError:
                            sleep_time = 0
                        self._context.wait_for_timeout(sleep_time * 1000)
                    else:
                        raise ValueError(f"Unsupported action type: {action_type}")
                return True
            except TimeoutError:
                raise TimeoutError(f'Task execution timeout when execute step: {step}')
            except Exception as e:
                raise Exception(f'Execute steps failed: {to_native(e)}')
            finally:
                browser.close()
