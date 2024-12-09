from django.views.generic import FormView
from django import forms
from django.utils.translation import gettext_lazy as _

from authentication import errors
from authentication.mixins import AuthMixin

__all__ = ['UserFaceCaptureView', 'UserFaceEnableView',
           'UserFaceDisableView']

from common.utils import FlashMessageUtil


class UserFaceCaptureForm(forms.Form):
    code = forms.CharField(label='MFA Code', max_length=128, required=False)


class UserFaceCaptureView(AuthMixin, FormView):
    template_name = 'authentication/face_capture.html'
    form_class = UserFaceCaptureForm
    mfa_type = 'face'
    code = ''

    def form_valid(self, form):
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if 'form' not in kwargs:
            form = self.get_form()
            context['form'] = form

        if not context['form'].is_bound:
            context.update({
                "active": True,
            })

        return context


class UserFaceEnableView(UserFaceCaptureView):
    def form_valid(self, form):
        try:
            code = self.get_face_code()
            user = self.get_user_from_session()
            user.face_vector = code
            user.save(update_fields=['face_vector'])
        except Exception as e:
            form.add_error("code", str(e))
            return super().form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        message_data = {
            'title': _('Face binding successful'),
            'message': _('Face binding successful'),
            'interval': 2,
            'redirect_url': '/ui/#/profile/index'
        }
        url = FlashMessageUtil.gen_message_url(message_data)
        return url


class UserFaceDisableView(UserFaceCaptureView):
    def form_valid(self, form):
        try:
            self._do_check_user_mfa(self.code, self.mfa_type)
            user = self.get_user_from_session()
            user.face_vector = None
            user.save(update_fields=['face_vector'])
        except (errors.MFAFailedError, errors.BlockMFAError) as e:
            form.add_error('code', e.msg)
            return super().form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        message_data = {
            'title': _('Face unbinding successful'),
            'message': _('Face unbinding successful'),
            'interval': 2,
            'redirect_url': '/ui/#/profile/index'
        }
        url = FlashMessageUtil.gen_message_url(message_data)
        return url
