from common.utils import (
    get_logger,
)
from django.conf import settings
from django.core.exceptions import ValidationError
from users.face_codec import get_face_codec

logger = get_logger(__file__)


class FaceMixin:
    face_vector = None

    @property
    def is_face_code_set(self):
        codec = get_face_codec()
        if not codec or not self.face_vector:
            return False
        return codec.is_native_code(str(self.face_vector))

    def get_face_vector(self) -> list[float]:
        if not self.face_vector:
            raise ValidationError("Face vector is not set.")
        codec = get_face_codec()
        if not codec:
            raise ValidationError("Face recognition backend is not available.")
        return codec.decode_code(str(self.face_vector))

    def check_face(
        self, code, distance_threshold=None, similarity_threshold=None
    ) -> bool:
        if not self.face_vector:
            raise ValidationError("Face vector is not set.")
        codec = get_face_codec()
        if not codec:
            raise ValidationError("Face recognition backend is not available.")
        distance_threshold = (
            settings.FACE_RECOGNITION_DISTANCE_THRESHOLD
            if distance_threshold is None
            else distance_threshold
        )
        similarity_threshold = (
            settings.FACE_RECOGNITION_COSINE_THRESHOLD
            if similarity_threshold is None
            else similarity_threshold
        )
        return codec.compare_codes(
            str(self.face_vector),
            code,
            cosine_threshold=similarity_threshold,
            distance_threshold=distance_threshold,
        )
