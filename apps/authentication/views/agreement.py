from django.views.generic import TemplateView
from django.utils.translation import get_language
from django.conf import settings


__all__ = ['UserAgreementView', 'PrivacyPolicyView']

class UserAgreementView(TemplateView):

    def get_template_names(self):
        current_lang = get_language() or 'zh-cn'
        lang_code = 'en'
        if current_lang.startswith('zh'):
            lang_code = 'zh'

        if settings.XPACK_ENABLED:
            return 'authentication/user_agreement_ee_{}.html'.format(lang_code)
        else:
             return 'authentication/user_agreement_{}.html'.format(lang_code)
        


class PrivacyPolicyView(TemplateView):
    def get_template_names(self):
        current_lang = get_language() or 'zh-cn'
        if current_lang.startswith('zh'):
            return 'authentication/privacy_policy_zh.html'
        else:
            return 'authentication/privacy_policy_en.html'