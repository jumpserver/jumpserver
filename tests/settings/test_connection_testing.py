"""Isolated source-boundary tests; no database or external service is contacted.

Run: python -m unittest discover -s tests/settings -v
Requires Django and DRF. Actual serializers and API methods are executed with
explicit substitutes for session decryption, SDKs, mail delivery and mounting.
These tests do not replace deployment integration tests.
"""
import ast
from collections import OrderedDict
from pathlib import Path
from smtplib import SMTPSenderRefused
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

from django.conf import settings as django_settings
from django.db import models

if not django_settings.configured:
    django_settings.configure(USE_I18N=False, SECRET_KEY='connection-tests')

from rest_framework import serializers, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

ROOT = Path(__file__).resolve().parents[2]


def load(path, names, namespace):
    tree = ast.parse((ROOT / path).read_text())
    body = [node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    assert {node.name for node in body} == set(names)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(ROOT / path), 'exec'), namespace)
    return namespace


def context(saved=None):
    ns = dict(
        settings=SimpleNamespace(**(saved or {})), serializers=serializers,
        models=models, TextChoices=models.TextChoices, _=lambda value: value,
        ValidationError=ValidationError, APIException=APIException, Response=Response,
        status=status, APIView=object, GenericAPIView=object, logger=Mock(),
        OrderedDict=OrderedDict,
        decrypt_session_password=Mock(side_effect=lambda value: value.removeprefix('encrypted:')),
    )
    load('apps/common/serializers/fields.py', ['EncryptedField'], ns)
    load('apps/settings/connection_testing.py', ['get_test_config', 'verify_im_credentials'], ns)
    return ns


class ConfigTests(unittest.TestCase):
    def test_current_falsy_values_and_saved_defaults_without_mutating_inputs(self):
        ns = context({'ENABLED': True, 'PORT': 123, 'PROXY': 'old', 'SECRET': 'saved'})

        class Config(serializers.Serializer):
            ENABLED = serializers.BooleanField(default=False)
            PORT = serializers.IntegerField()
            PROXY = serializers.CharField(allow_blank=True)
            SECRET = ns['EncryptedField'](required=False)

        draft = {'ENABLED': False, 'PORT': 0, 'PROXY': '', 'SECRET': ''}
        result = ns['get_test_config'](Config, draft)
        self.assertEqual(result, {**draft, 'SECRET': 'saved'})
        self.assertEqual(draft['SECRET'], '')
        self.assertEqual(vars(ns['settings']), dict(ENABLED=True, PORT=123, PROXY='old', SECRET='saved'))
        ns['decrypt_session_password'].assert_not_called()
        self.assertTrue(ns['get_test_config'](Config, {})['ENABLED'])
        result = ns['get_test_config'](Config, {'SECRET': 'encrypted:new'})
        self.assertEqual(result['SECRET'], 'new')
        ns['decrypt_session_password'].assert_called_once_with('encrypted:new')

    def test_missing_required_secret_is_a_field_error(self):
        ns = context()

        class Config(serializers.Serializer):
            SECRET = ns['EncryptedField'](required=False)

        with self.assertRaises(ValidationError) as error:
            ns['get_test_config'](Config, {}, ('SECRET',))
        self.assertIn('SECRET', error.exception.detail)

    def test_nas_validates_without_save_serializer_or_mount_side_effects(self):
        ns = context(dict(NAS_TYPE='cifs', NAS_HOST='saved', NAS_PORT=445,
                          NAS_SHARE_NAME='share', NAS_USERNAME='user', NAS_PASSWORD='saved'))
        load('apps/settings/serializers/storage.py', ['NasTestSerializer'], ns)
        load('apps/settings/api/nas.py', ['NasTestingAPI'], ns)
        probe = Mock(return_value=(False, 'not writable'))
        with patch.dict(sys.modules, {'settings.tools.nas_mount': SimpleNamespace(test_nas_connection=probe)}):
            response = ns['NasTestingAPI']().post(SimpleNamespace(data={
                'NAS_HOST': 'draft', 'NAS_PORT': 0, 'NAS_PASSWORD': 'encrypted:new'
            }))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(probe.call_args.args[0]['nas_password'], 'new')
        self.assertEqual(probe.call_args.args[0]['nas_host'], 'draft')
        self.assertEqual(probe.call_args.args[0]['nas_port'], 0)
        self.assertEqual(ns['settings'].NAS_PASSWORD, 'saved')
        with self.assertRaises(ValidationError):
            ns['get_test_config'](ns['NasTestSerializer'], {'NAS_USERNAME': ''})
        with self.assertRaises(ValidationError):
            ns['get_test_config'](ns['NasTestSerializer'], {'NAS_PORT': 65536})
        nfs = ns['get_test_config'](ns['NasTestSerializer'], {'NAS_TYPE': 'nfs', 'NAS_USERNAME': ''})
        self.assertEqual(nfs['NAS_PASSWORD'], 'saved')


class MailTests(unittest.TestCase):
    def setUp(self):
        self.ns = context(dict(
            EMAIL_PROTOCOL='smtp', EMAIL_HOST='saved', EMAIL_PORT=465,
            EMAIL_HOST_USER='user@example.com', EMAIL_HOST_PASSWORD='saved',
            EMAIL_FROM='', EMAIL_RECIPIENT='', EMAIL_USE_SSL=True, EMAIL_USE_TLS=False,
            EMAIL_SUBJECT_PREFIX='Test',
        ))
        load('apps/settings/serializers/msg.py', ['EmailSettingSerializer', 'MailTestSerializer'], self.ns)

    def test_smtp_draft_and_exchange_hidden_fields(self):
        ns = self.ns
        config = ns['get_test_config'](ns['MailTestSerializer'], {
            'EMAIL_HOST': 'draft', 'EMAIL_PORT': '587', 'EMAIL_USE_SSL': False, 'EMAIL_USE_TLS': True
        })
        self.assertEqual((config['EMAIL_HOST'], config['EMAIL_PORT']), ('draft', 587))
        self.assertFalse(config['EMAIL_USE_SSL'])
        config = ns['get_test_config'](ns['MailTestSerializer'], {
            'EMAIL_PROTOCOL': 'exchange', 'EMAIL_PORT': '', 'EMAIL_USE_TLS': True
        })
        self.assertNotIn('EMAIL_PORT', config)
        for invalid in ({'EMAIL_PORT': 0}, {'EMAIL_USE_TLS': True}):
            with self.assertRaises(ValidationError):
                ns['get_test_config'](ns['MailTestSerializer'], invalid)

    def test_connection_factory_preserves_production_default_and_maps_exchange(self):
        ns = self.ns
        ns['get_connection'] = Mock()
        load('apps/common/tasks.py', ['get_email_connection'], ns)
        ns['get_email_connection']()
        ns['get_connection'].assert_called_with(backend='django.core.mail.backends.smtp.EmailBackend')
        ns['get_email_connection'](protocol='exchange', host='https://draft/ews', username='new')
        ns['get_connection'].assert_called_with(
            backend='jumpserver.rewriting.exchange.EmailBackend',
            service_endpoint='https://draft/ews', username='new'
        )
        self.assertEqual(ns['settings'].EMAIL_PROTOCOL, 'smtp')

    def test_mail_api_uses_draft_and_closes_on_success_and_failure(self):
        ns = self.ns
        ns.update(serializers=SimpleNamespace(MailTestSerializer=ns['MailTestSerializer']),
                  get_connection=Mock(), send_mail=Mock(), SMTPSenderRefused=SMTPSenderRefused)
        load('apps/settings/api/email.py', ['MailTestingAPI'], ns)
        for failure in (None, RuntimeError('delivery failed')):
            ns['send_mail'].side_effect = failure
            ns['get_connection'].reset_mock()
            response = ns['MailTestingAPI']().post(SimpleNamespace(data={
                'EMAIL_HOST': 'draft', 'EMAIL_HOST_PASSWORD': 'encrypted:new',
                'EMAIL_USE_SSL': False, 'EMAIL_RECIPIENT': 'test@example.com',
            }))
            self.assertEqual(response.status_code, 400 if failure else 200)
            kwargs = ns['get_connection'].call_args.kwargs
            self.assertEqual((kwargs['host'], kwargs['password'], kwargs['use_ssl']), ('draft', 'new', False))
            ns['get_connection'].return_value.close.assert_called_once()
            self.assertEqual(ns['send_mail'].call_args.args[3], ['test@example.com'])
            self.assertEqual(ns['settings'].EMAIL_HOST, 'saved')


class SMSTests(unittest.TestCase):
    def setUp(self):
        ns = context(dict(SMS_CODE_LENGTH=4, CUSTOM_SMS_URL='https://saved.example',
                          CUSTOM_SMS_REQUEST_METHOD='get',
                          CUSTOM_SMS_API_PARAMS={'to': '{phone_numbers}', 'code': '{code}'},
                          VERIFY_EXTERNAL_SSL=True))
        ns.update(PhoneField=serializers.CharField, PhoneValidator=lambda: lambda value: None,
                  BACKENDS=SimpleNamespace(choices=[('alibaba', 'Alibaba')], ALIBABA='alibaba'))
        names = ['SMSSettingSerializer', 'BaseSMSSettingSerializer', 'AlibabaSMSSettingSerializer',
                 'TencentSMSSettingSerializer', 'HuaweiSMSSettingSerializer', 'CMPP2SMSSettingSerializer',
                 'CustomSMSSettingSerializer']
        load('apps/settings/serializers/auth/sms.py', names, ns)
        self.classes = SimpleNamespace(
            **{name: ns[name] for name in names}, ValidationError=ValidationError
        )
        ns.update(serializers=self.classes, JMSException=APIException, importlib=Mock(), __package__='settings.api')
        load('apps/settings/api/sms.py', ['SMSTestingAPI'], ns)
        self.ns = ns

    def test_custom_api_passes_parent_length_and_current_provider_configuration(self):
        ns = self.ns
        response = ns['SMSTestingAPI']().post(SimpleNamespace(data={
            'CUSTOM_SMS_URL': 'https://draft.example/send', 'CUSTOM_SMS_REQUEST_METHOD': 'post',
            'CUSTOM_SMS_API_PARAMS': {'recipient': '{phone_numbers}', 'text': '{code}'},
            'SMS_CODE_LENGTH': 8, 'SMS_TEST_PHONE': '+8613800000000',
        }), 'custom')
        self.assertEqual(response.status_code, 200)
        client = ns['importlib'].import_module.return_value.client
        self.assertEqual(client.call_args.kwargs['url'], 'https://draft.example/send')
        self.assertEqual(client.call_args.kwargs['method'], 'post')
        self.assertEqual(client.return_value.send_sms.call_args.kwargs['template_param']['code'], '66666666')
        self.assertEqual(ns['settings'].SMS_CODE_LENGTH, 4)
        with self.assertRaises(ValidationError):
            ns['SMSTestingAPI']().post(SimpleNamespace(data={'SMS_CODE_LENGTH': 0}), 'custom')
        with self.assertRaises(APIException):
            ns['SMSTestingAPI']().post(SimpleNamespace(data={'SMS_TEST_PHONE': ''}), 'custom')

    def test_cmpp2_new_secret_and_invalid_custom_json(self):
        api = self.ns['SMSTestingAPI']()
        api.test_code_length = 6
        data = dict(CMPP2_HOST='draft', CMPP2_PORT=7890, CMPP2_SP_ID='id', CMPP2_SRC_ID='src',
                    CMPP2_SP_SECRET='new', CMPP2_SERVICE_ID='service',
                    CMPP2_VERIFY_SIGN_NAME='sign', CMPP2_VERIFY_TEMPLATE_CODE='{code}')
        init, send = api.get_cmpp2_params(data)
        self.assertEqual(init['sp_secret'], 'new')
        self.assertEqual(send['template_param']['code'], '666666')
        for invalid in ([], {'code': 123}, None):
            with self.assertRaises(ValidationError):
                self.ns['get_test_config'](self.classes.CustomSMSSettingSerializer, {'CUSTOM_SMS_API_PARAMS': invalid})

    def test_custom_sdk_get_post_and_normal_saved_defaults(self):
        ns = self.ns
        ns.update(BaseSMSClient=object, requests=Mock())
        load('apps/common/sdk/sms/custom.py', ['CustomSMS'], ns)
        for method, key in (('get', 'params'), ('post', 'json')):
            ns['CustomSMS']('https://draft.example', method, {'msg': '{code}', 'to': '{phone_numbers}'}, timeout=30).send_sms(
                ['123'], OrderedDict(code='666666')
            )
            getattr(ns['requests'], method).assert_called_once_with(
                url='https://draft.example', verify=True, timeout=30,
                **{key: {'msg': '666666', 'to': '123'}}
            )
        self.assertEqual(ns['CustomSMS'].new_from_settings().url, 'https://saved.example')
        self.assertIsNone(ns['CustomSMS'].new_from_settings().timeout)


class ChatTests(unittest.TestCase):
    def setUp(self):
        ns = context(dict(
            CHAT_AI_ENABLED=True, CHAT_AI_METHOD='api', CHAT_AI_TYPE='gpt',
            CHAT_AI_EMBED_URL='', GPT_BASE_URL='https://saved.example',
            GPT_API_KEY='saved-gpt', GPT_PROXY='http://old-proxy', GPT_MODEL='custom',
            CUSTOM_GPT_MODEL='saved-model', DEEPSEEK_BASE_URL='', DEEPSEEK_API_KEY='saved-deepseek',
            DEEPSEEK_PROXY='', DEEPSEEK_MODEL='deepseek-chat', CUSTOM_DEEPSEEK_MODEL='',
        ))
        load('apps/settings/const.py',
             ['ChatAIMethodChoices', 'ChatAITypeChoices', 'GPTModelChoices', 'DeepSeekModelChoices'], ns)
        load('apps/settings/serializers/feature.py', ['ChatAISettingSerializer'], ns)
        ns.update(serializers=SimpleNamespace(ChatAISettingSerializer=ns['ChatAISettingSerializer']),
                  httpx=Mock(), openai=SimpleNamespace(OpenAI=Mock(), APIConnectionError=type('ConnectionError', (Exception,), {}),
                                                     APIStatusError=type('StatusError', (Exception,), {})))
        load('apps/settings/api/chat.py', ['ChatAITestingAPI'], ns)
        self.ns = ns

    def test_draft_clears_proxy_uses_new_key_and_custom_model(self):
        ns = self.ns
        response = ns['ChatAITestingAPI']().post(SimpleNamespace(data={
            'GPT_PROXY': '', 'GPT_API_KEY': 'encrypted:new', 'CUSTOM_GPT_MODEL': 'draft-model'
        }))
        self.assertEqual(response.status_code, 200)
        ns['httpx'].Client.assert_not_called()
        self.assertEqual(ns['openai'].OpenAI.call_args.kwargs['api_key'], 'new')
        client = ns['openai'].OpenAI.return_value
        self.assertEqual(client.chat.completions.create.call_args.kwargs['model'], 'draft-model')
        client.close.assert_called_once()
        self.assertEqual(ns['settings'].GPT_PROXY, 'http://old-proxy')

    def test_disabled_or_embed_does_not_call_provider(self):
        ns = self.ns
        for draft in ({'CHAT_AI_ENABLED': False}, {'CHAT_AI_METHOD': 'embed'}):
            response = ns['ChatAITestingAPI']().post(SimpleNamespace(data=draft))
            self.assertEqual(response.status_code, 400)
        ns['openai'].OpenAI.assert_not_called()

    def test_deepseek_uses_own_saved_secret_and_failure_closes_client(self):
        ns = self.ns
        ns['openai'].OpenAI.return_value.chat.completions.create.side_effect = RuntimeError('failed')
        response = ns['ChatAITestingAPI']().post(SimpleNamespace(data={'CHAT_AI_TYPE': 'deep-seek'}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ns['openai'].OpenAI.call_args.kwargs['api_key'], 'saved-deepseek')
        ns['openai'].OpenAI.return_value.close.assert_called_once()

    def test_constructor_failure_closes_proxy_client(self):
        ns = self.ns
        ns['openai'].OpenAI.side_effect = RuntimeError('failed')
        response = ns['ChatAITestingAPI']().post(SimpleNamespace(data={}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ns['httpx'].Client.call_args.kwargs['proxy'], 'http://old-proxy')
        ns['httpx'].Client.return_value.close.assert_called_once()


class IMTests(unittest.TestCase):
    def test_slack_uses_saved_or_draft_bot_token_and_reports_failure(self):
        ns = context(dict(SLACK_CLIENT_ID='client', SLACK_BOT_TOKEN='saved-token'))
        ns['OrgListField'] = lambda: serializers.ListField(required=False)
        load('apps/settings/serializers/auth/slack.py', ['SlackSettingSerializer'], ns)
        ns.update(serializers=SimpleNamespace(SlackSettingSerializer=ns['SlackSettingSerializer']),
                  Slack=Mock(), RequestException=ConnectionError)
        load('apps/settings/api/slack.py', ['SlackTestingAPI'], ns)
        for draft, token in (({}, 'saved-token'), ({'SLACK_BOT_TOKEN': 'encrypted:new'}, 'new')):
            response = ns['SlackTestingAPI']().post(SimpleNamespace(data=draft))
            self.assertEqual(response.status_code, 200)
            ns['Slack'].assert_called_with(bot_token=token)
            ns['Slack'].return_value.is_valid.assert_called_with(timeout=30)
        ns['Slack'].return_value.is_valid.side_effect = APIException('invalid_auth')
        self.assertEqual(ns['SlackTestingAPI']().post(SimpleNamespace(data={})).status_code, 400)
        self.assertEqual(ns['settings'].SLACK_BOT_TOKEN, 'saved-token')

    def test_token_probe_bypasses_production_cache_and_propagates_failure(self):
        ns = context()
        ns.update(RequestMixin=object, lazyproperty=property, as_request=lambda func: func, DictWrapper=dict)
        load('apps/common/sdk/im/mixin.py', ['BaseRequest'], ns)
        for failure in (None, APIException('invalid credentials')):
            request_token = Mock(return_value=('fresh', 7200), side_effect=failure)
            cache = Mock()
            ns['cache'] = cache

            class Provider(ns['BaseRequest']):
                request_access_token = request_token

                def get_access_token_cache_key(self):
                    return 'production'

            if failure:
                with self.assertRaises(APIException):
                    ns['verify_im_credentials'](Provider)
            else:
                client = ns['verify_im_credentials'](Provider)
                self.assertEqual(client.access_token, 'fresh')
                self.assertEqual(client._request_kwargs['timeout'], 30)
            request_token.assert_called_once()
            self.assertEqual(cache.mock_calls, [])

    def test_im_apis_use_current_secrets_and_report_provider_errors(self):
        for category, api, serializer, fields, sdk in (
            ('wecom', 'WeComTestingAPI', 'WeComSettingSerializer',
             {'WECOM_CORPID': 'new', 'WECOM_AGENTID': 'agent', 'WECOM_SECRET': 'new-secret'}, 'WeComRequests'),
            ('dingtalk', 'DingTalkTestingAPI', 'DingTalkSettingSerializer',
             {'DINGTALK_APPKEY': 'new', 'DINGTALK_AGENTID': 'agent', 'DINGTALK_APPSECRET': 'new-secret'}, 'DingTalkRequests'),
            ('feishu', 'FeiShuTestingAPI', 'FeiShuSettingSerializer',
             {'FEISHU_APP_ID': 'new', 'FEISHU_APP_SECRET': 'new-secret'}, 'FeishuRequests'),
            ('lark', 'FeiShuTestingAPI', 'LarkSettingSerializer',
             {'LARK_APP_ID': 'new', 'LARK_APP_SECRET': 'new-secret'}, 'LarkRequests'),
        ):
            with self.subTest(category=category):
                ns = context()
                ns['OrgListField'] = lambda: serializers.ListField(required=False)
                load(f'apps/settings/serializers/auth/{category}.py', [serializer], ns)
                ns.update(serializers=SimpleNamespace(**{serializer: ns[serializer], 'FeiShuSettingSerializer': ns[serializer]}),
                          RequestException=ConnectionError, verify_im_credentials=Mock(),
                          WeComRequests=object(), DingTalkRequests=object(), FeishuRequests=object(), LarkRequests=object())
                load(f'apps/settings/api/{"feishu" if category == "lark" else category}.py', [api], ns)
                view = ns[api]()
                if category == 'lark':
                    view.category = 'LARK'
                for failure in (None, APIException({'msg': 'invalid credentials'}), ConnectionError()):
                    ns['verify_im_credentials'].side_effect = failure
                    response = view.post(SimpleNamespace(data=fields))
                    self.assertEqual(response.status_code, 400 if failure else 200)
                    args, kwargs = ns['verify_im_credentials'].call_args
                    self.assertIs(args[0], ns[sdk])
                    self.assertIn('new-secret', kwargs.values())


if __name__ == '__main__':
    unittest.main()
