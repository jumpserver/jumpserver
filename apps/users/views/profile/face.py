from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.views.generic import FormView
from django import forms

from authentication import errors
from authentication.mixins import AuthMixin, MFAFaceMixin

__all__ = ['UserFaceCaptureView', 'UserFaceEnableView',
           'UserFaceDisableView']


class UserFaceCaptureForm(forms.Form):
    code = forms.CharField(label='MFA Code', max_length=128, required=False)


class UserFaceCaptureView(AuthMixin, FormView):
    template_name = 'authentication/face_capture.html'
    form_class = UserFaceCaptureForm
    mfa_type = 'face'
    code = ''

    def form_valid(self, form):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data()

        if not self.get_form().is_bound:
            context.update({
                "active": True,
            })

        kwargs.update(context)
        return kwargs


class UserFaceEnableView(UserFaceCaptureView, MFAFaceMixin):
    def form_valid(self, form):
        code = self.get_face_code()

        user = self.get_user_from_session()
        user.face_vector = code
        user.save(update_fields=['face_vector'])

        auth_logout(self.request)
        return redirect('authentication:login')


class UserFaceDisableView(UserFaceCaptureView):
    def form_valid(self, form):
        try:
            self._do_check_user_mfa(self.code, self.mfa_type)
            user = self.get_user_from_session()
            user.face_vector = None
            user.save(update_fields=['face_vector'])
            auth_logout(self.request)
        except (errors.MFAFailedError, errors.BlockMFAError) as e:
            form.add_error('code', e.msg)
            return super().form_invalid(form)

        return redirect('authentication:login')
