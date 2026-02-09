from django.views.generic import TemplateView
from django.utils.translation import get_language

__all__ = ['UserAgreementView', 'PrivacyPolicyView']

class UserAgreementView(TemplateView):

    def get_template_names(self):
        current_lang = get_language() or 'zh-cn'
        if current_lang.startswith('zh'):
            return 'authentication/user_agreement_zh.html'
        else:
            return 'authentication/user_agreement.html'


class PrivacyPolicyView(TemplateView):
    def get_template_names(self):
        current_lang = get_language() or 'zh-cn'
        if current_lang.startswith('zh'):
            return 'authentication/privacy_policy_zh.html'
        else:
            return 'authentication/privacy_policy_en.html'