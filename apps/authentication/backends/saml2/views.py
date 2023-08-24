import copy

from urllib import parse

from django.views import View
from django.contrib import auth
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseServerError

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.errors import OneLogin_Saml2_Error
from onelogin.saml2.idp_metadata_parser import (
    OneLogin_Saml2_IdPMetadataParser as IdPMetadataParse,
    dict_deep_merge
)

from .settings import JmsSaml2Settings

from common.utils import get_logger

logger = get_logger(__file__)


class PrepareRequestMixin:
    @staticmethod
    def is_secure():
        url_result = parse.urlparse(settings.SITE_URL)
        return 'on' if url_result.scheme == 'https' else 'off'

    def prepare_django_request(self, request):
        result = {
            'https': self.is_secure(),
            'http_host': request.META['HTTP_HOST'],
            'script_name': request.META['PATH_INFO'],
            'get_data': request.GET.copy(),
            'post_data': request.POST.copy()
        }
        return result

    @staticmethod
    def get_idp_settings():
        idp_metadata_xml = settings.SAML2_IDP_METADATA_XML
        idp_metadata_url = settings.SAML2_IDP_METADATA_URL
        logger.debug('Start getting IDP configuration')

        xml_idp_settings = None
        try:
            if idp_metadata_xml.strip():
                xml_idp_settings = IdPMetadataParse.parse(idp_metadata_xml)
        except Exception as err:
            logger.warning('Failed to get IDP metadata XML settings, error: %s', str(err))

        url_idp_settings = None
        try:
            if idp_metadata_url.strip():
                url_idp_settings = IdPMetadataParse.parse_remote(
                    idp_metadata_url, timeout=20
                )
        except Exception as err:
            logger.warning('Failed to get IDP metadata URL settings, error: %s', str(err))

        idp_settings = url_idp_settings or xml_idp_settings

        if idp_settings is None:
            msg = 'Unable to resolve IDP settings. '
            tip = 'Please contact your administrator to check system settings,' \
                  'or login using other methods.'
            logger.error(msg)
            raise OneLogin_Saml2_Error(msg + tip, OneLogin_Saml2_Error.SETTINGS_INVALID)

        logger.debug('IDP settings obtained successfully')
        return idp_settings

    @staticmethod
    def get_request_attributes():
        attr_mapping = settings.SAML2_RENAME_ATTRIBUTES or {}
        attr_map_reverse = {v: k for k, v in attr_mapping.items()}
        need_attrs = (
            ('username', 'username', True),
            ('email', 'email', True),
            ('name', 'name', False),
            ('phone', 'phone', False),
            ('comment', 'comment', False),
        )
        attr_list = []
        for name, friend_name, is_required in need_attrs:
            rename_name = attr_map_reverse.get(friend_name)
            name = rename_name if rename_name else name
            attr_list.append({
                "name": name, "isRequired": is_required,
                "friendlyName": friend_name,
            })
        return attr_list

    def get_attribute_consuming_service(self):
        attr_list = self.get_request_attributes()
        request_attribute_template = {
            "attributeConsumingService": {
                "isDefault": False,
                "serviceName": "JumpServer",
                "serviceDescription": "JumpServer",
                "requestedAttributes": attr_list
            }
        }
        return request_attribute_template

    @staticmethod
    def get_advanced_settings():
        try:
            other_settings = dict(settings.SAML2_SP_ADVANCED_SETTINGS)
            other_settings = copy.deepcopy(other_settings)
        except Exception as error:
            logger.error('Get other settings error: %s', error)
            other_settings = {}

        security_default = {
            'wantAttributeStatement': False,
            'allowRepeatAttributeName': True
        }
        security = other_settings.get('security', {})
        security_default.update(security)

        default = {
            "organization": {
                "en": {
                    "name": "JumpServer",
                    "displayname": "JumpServer",
                    "url": "https://jumpserver.org/"
                }
            },
        }
        default.update(other_settings)
        default['security'] = security_default
        return default

    def get_sp_settings(self):
        sp_host = settings.SITE_URL
        attrs = self.get_attribute_consuming_service()
        sp_settings = {
            'sp': {
                'entityId': f"{sp_host}{reverse('authentication:saml2:saml2-login')}",
                'assertionConsumerService': {
                    'url': f"{sp_host}{reverse('authentication:saml2:saml2-callback')}",
                },
                'singleLogoutService': {
                    'url': f"{sp_host}{reverse('authentication:saml2:saml2-logout')}"
                },
                'privateKey': getattr(settings, 'SAML2_SP_KEY_CONTENT', ''),
                'x509cert': getattr(settings, 'SAML2_SP_CERT_CONTENT', ''),
            }
        }
        sp_settings['sp'].update(attrs)
        advanced_settings = self.get_advanced_settings()
        sp_settings.update(advanced_settings)
        return sp_settings

    def get_saml2_settings(self):
        sp_settings = self.get_sp_settings()
        idp_settings = self.get_idp_settings()
        saml2_settings = dict_deep_merge(sp_settings, idp_settings)
        return saml2_settings

    def init_saml_auth(self, request):
        request = self.prepare_django_request(request)
        _settings = self.get_saml2_settings()
        saml_instance = OneLogin_Saml2_Auth(
            request, old_settings=_settings, custom_base_path=settings.SAML_FOLDER
        )
        return saml_instance

    @staticmethod
    def value_to_str(attr):
        if isinstance(attr, str):
            return attr
        elif isinstance(attr, list) and len(attr) > 0:
            return str(attr[0])

    def get_attributes(self, saml_instance):
        user_attrs = {}
        attr_mapping = settings.SAML2_RENAME_ATTRIBUTES
        attrs = saml_instance.get_attributes()
        valid_attrs = ['username', 'name', 'email', 'comment', 'phone']

        for attr, value in attrs.items():
            attr = attr.rsplit('/', 1)[-1]
            if attr_mapping and attr_mapping.get(attr):
                attr = attr_mapping.get(attr)
            if attr not in valid_attrs:
                continue
            user_attrs[attr] = self.value_to_str(value)
        return user_attrs


class Saml2AuthRequestView(View, PrepareRequestMixin):

    def get(self, request):
        log_prompt = "Process SAML GET requests: {}"
        logger.debug(log_prompt.format('Start'))

        try:
            saml_instance = self.init_saml_auth(request)
        except OneLogin_Saml2_Error as error:
            logger.error(log_prompt.format('Init saml auth error: %s' % error))
            return HttpResponse(error, status=412)

        next_url = settings.AUTH_SAML2_PROVIDER_AUTHORIZATION_ENDPOINT
        url = saml_instance.login(return_to=next_url)
        logger.debug(log_prompt.format('Redirect login url'))
        return HttpResponseRedirect(url)


class Saml2EndSessionView(View, PrepareRequestMixin):
    http_method_names = ['get', 'post', ]

    def get(self, request):
        log_prompt = "Process SAML GET requests: {}"
        logger.debug(log_prompt.format('Start'))
        return self.post(request)

    def post(self, request):
        log_prompt = "Process SAML POST requests: {}"
        logger.debug(log_prompt.format('Start'))

        logout_url = settings.LOGOUT_REDIRECT_URL or '/'

        if request.user.is_authenticated:
            logger.debug(log_prompt.format('Log out the current user: {}'.format(request.user)))
            auth.logout(request)

            if settings.SAML2_LOGOUT_COMPLETELY:
                saml_instance = self.init_saml_auth(request)
                logger.debug(log_prompt.format('Log out IDP user session synchronously'))
                return HttpResponseRedirect(saml_instance.logout())

        logger.debug(log_prompt.format('Redirect logout url'))
        return HttpResponseRedirect(logout_url)


class Saml2AuthCallbackView(View, PrepareRequestMixin):

    def post(self, request):
        log_prompt = "Process SAML2 POST requests: {}"
        post_data = request.POST

        try:
            saml_instance = self.init_saml_auth(request)
        except OneLogin_Saml2_Error as error:
            logger.error(log_prompt.format('Init saml auth error: %s' % error))
            return HttpResponse(error, status=412)

        request_id = None
        if 'AuthNRequestID' in request.session:
            request_id = request.session['AuthNRequestID']

        logger.debug(log_prompt.format('Process saml response'))
        saml_instance.process_response(request_id=request_id)
        errors = saml_instance.get_last_error_reason()

        if errors:
            logger.error(log_prompt.format('Saml response has error: %s' % str(errors)))
            return HttpResponseRedirect(settings.AUTH_SAML2_AUTHENTICATION_FAILURE_REDIRECT_URI)

        if 'AuthNRequestID' in request.session:
            del request.session['AuthNRequestID']

        logger.debug(log_prompt.format('Process authenticate'))
        saml_user_data = self.get_attributes(saml_instance)
        user = auth.authenticate(request=request, saml_user_data=saml_user_data)
        if user and user.is_valid:
            logger.debug(log_prompt.format('Login: {}'.format(user)))
            auth.login(self.request, user)

        logger.debug(log_prompt.format('Redirect'))
        redir = post_data.get('RelayState')
        if not redir or len(redir) == 0:
          redir = "/"
        next_url = saml_instance.redirect_to(redir)
        return HttpResponseRedirect(next_url)

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class Saml2AuthMetadataView(View, PrepareRequestMixin):

    def get(self, request):
        saml_settings = self.get_sp_settings()
        saml_settings = JmsSaml2Settings(
            settings=saml_settings, sp_validation_only=True,
            custom_base_path=settings.SAML_FOLDER
        )
        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)

        key = saml_settings.get_sp_key()
        cert = saml_settings.get_sp_cert()
        if not key:
            errors.append('Not found SP private key')
        if not cert:
            errors.append('Not found SP cert')

        if len(errors) == 0:
            resp = HttpResponse(content=metadata, content_type='text/xml')
        else:
            content = "Error occur: <br>"
            content += '<br>'.join(errors)
            resp = HttpResponseServerError(content=content)
        return resp
