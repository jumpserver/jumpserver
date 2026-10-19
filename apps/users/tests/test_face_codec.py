from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings
from users.face_codec import FaceCodecAdapter
from users.models.user._face import FaceMixin


class FaceSubject(FaceMixin):
    pass


class FaceCodecAdapterTest(SimpleTestCase):
    @patch("users.face_codec._adapter", None)
    def test_face_is_unavailable_without_xpack_adapter(self):
        subject = FaceSubject()
        subject.face_vector = "enterprise-face-code"

        self.assertFalse(subject.is_face_code_set)
        with self.assertRaisesRegex(ValidationError, "backend is not available"):
            subject.check_face("candidate-face-code")
        with self.assertRaisesRegex(ValidationError, "backend is not available"):
            subject.get_face_vector()

    @override_settings(
        FACE_RECOGNITION_DISTANCE_THRESHOLD=0.35,
        FACE_RECOGNITION_COSINE_THRESHOLD=0.45,
    )
    def test_registered_adapter_handles_native_face_codes(self):
        is_native_code = Mock(return_value=True)
        compare_codes = Mock(return_value=True)
        decode_code = Mock(return_value=[1.0, 2.0])
        adapter = FaceCodecAdapter(
            is_native_code=is_native_code,
            compare_codes=compare_codes,
            decode_code=decode_code,
        )
        subject = FaceSubject()
        subject.face_vector = "native-face-code"

        with patch("users.face_codec._adapter", adapter):
            self.assertTrue(subject.is_face_code_set)
            self.assertTrue(subject.check_face("candidate-face-code"))
            self.assertEqual(subject.get_face_vector(), [1.0, 2.0])

        is_native_code.assert_called_once_with("native-face-code")
        compare_codes.assert_called_once_with(
            "native-face-code",
            "candidate-face-code",
            cosine_threshold=0.45,
            distance_threshold=0.35,
        )
        decode_code.assert_called_once_with("native-face-code")
