from django.views.generic import TemplateView
from django.utils.translation import get_language

__all__ = ['AgreementView']

class AgreementView(TemplateView):

    def get_template_names(self):
        current_lang = get_language() or 'zh-cn'
        if current_lang.startswith('zh'):
            return 'authentication/agreement_zh.html'
        else:
            return 'authentication/agreement.html'
