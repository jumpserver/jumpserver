import base64
import struct

import math
from django.conf import settings
from django.core.exceptions import ValidationError

from common.utils import (
    get_logger,
)

logger = get_logger(__file__)


class FaceMixin:
    face_vector = None

    @property
    def is_face_code_set(self):
        return self.face_vector is not None

    def get_face_vector(self) -> list[float]:
        if not self.face_vector:
            raise ValidationError("Face vector is not set.")
        return self._decode_base64_vector(str(self.face_vector))

    def check_face(self, code) -> bool:
        distance = self.compare_euclidean_distance(code)
        similarity = self.compare_cosine_similarity(code)

        return distance < settings.FACE_RECOGNITION_DISTANCE_THRESHOLD \
            and similarity > settings.FACE_RECOGNITION_COSINE_THRESHOLD

    def compare_euclidean_distance(self, base64_vector: str) -> float:
        target_vector = self._decode_base64_vector(base64_vector)
        current_vector = self.get_face_vector()
        return self._calculate_euclidean_distance(current_vector, target_vector)

    def compare_cosine_similarity(self, base64_vector: str) -> float:
        target_vector = self._decode_base64_vector(base64_vector)
        current_vector = self.get_face_vector()
        return self._calculate_cosine_similarity(current_vector, target_vector)

    @staticmethod
    def _decode_base64_vector(base64_vector: str) -> list[float]:
        byte_data = base64.b64decode(base64_vector)
        return list(struct.unpack('<128d', byte_data))

    @staticmethod
    def _calculate_euclidean_distance(vec1: list[float], vec2: list[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(vec1, vec2)) ** 0.5

    @staticmethod
    def _calculate_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        dot_product = sum(x * y for x, y in zip(vec1, vec2))
        magnitude_vec1 = math.sqrt(sum(x ** 2 for x in vec1))
        magnitude_vec2 = math.sqrt(sum(y ** 2 for y in vec2))
        if magnitude_vec1 == 0 or magnitude_vec2 == 0:
            raise ValueError("Vector magnitude cannot be zero.")
        return dot_product / (magnitude_vec1 * magnitude_vec2)
