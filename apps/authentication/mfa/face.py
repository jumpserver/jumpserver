from django.core.cache import cache

from authentication.mfa.base import BaseMFA
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _

from authentication.mixins import MFAFaceMixin
from settings.api import settings


class MFAFace(BaseMFA, MFAFaceMixin):
    name = "face"
    display_name = _('Face Recognition')
    placeholder = 'Face Recognition'

    def check_code(self, code):

        assert self.is_authenticated()

        try:
            code = self.get_face_code()
            if not self.user.check_face(code):
                return False, _('Facial comparison failed')
        except Exception as e:
            return False, "{}:{}".format(_('Facial comparison failed'), str(e))
        return True, ''

    def is_active(self):
        if not self.is_authenticated():
            return True
        return bool(self.user.face_vector)

    @staticmethod
    def global_enabled():
        return settings.XPACK_LICENSE_IS_VALID \
            and settings.XPACK_LICENSE_EDITION == 'ultimate' \
            and settings.FACE_RECOGNITION_ENABLED

    def get_enable_url(self) -> str:
        return reverse('authentication:user-face-enable')

    def get_disable_url(self) -> str:
        return reverse('authentication:user-face-disable')

    def disable(self):
        assert self.is_authenticated()
        self.user.face_vector = ''
        self.user.save(update_fields=['face_vector'])

    def can_disable(self) -> bool:
        return True

    @staticmethod
    def help_text_of_enable():
        return _("Frontal Face Recognition")
