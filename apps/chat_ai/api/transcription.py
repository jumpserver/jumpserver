import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from asgiref.sync import async_to_sync
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_field
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsValidUser
from jumpserver.views.schema import CustomAutoSchema

from chat_ai.permissions import CanUseChatAI, ChatAIOrgPermission, ChatAIServicePermission
from chat_ai.providers import get_transcription_provider
from chat_ai.providers.speech import (
    SpeechToTextConfigurationError, SpeechToTextError, SpeechToTextInputError,
    SpeechToTextRateLimitError, SpeechToTextTimeoutError,
)
from chat_ai.throttling import TranscriptionConcurrency, TranscriptionThrottle


AUDIO_CONTENT_TYPES = {
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.mp3': 'audio/mpeg',
    '.mp4': 'audio/mp4',
    '.mpeg': 'audio/mpeg',
    '.mpga': 'audio/mpeg',
    '.ogg': 'audio/ogg',
    '.wav': 'audio/wav',
    '.webm': 'audio/webm',
}


class AudioFileTooLarge(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'Audio file exceeds the configured size limit.'
    default_code = 'audio_file_too_large'


class AudioTooLong(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Audio duration exceeds the configured limit.'
    default_code = 'audio_too_long'


class AudioInspectionUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Audio inspection is unavailable.'
    default_code = 'audio_inspection_unavailable'


class TranscriptionBusy(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Too many speech-to-text requests are running.'
    default_code = 'transcription_busy'


class TranscriptionCapacityUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Speech-to-text concurrency control is unavailable.'
    default_code = 'transcription_capacity_unavailable'


@extend_schema_field(OpenApiTypes.BINARY)
class AudioFileField(serializers.FileField):
    pass


class TranscriptionRequestSerializer(serializers.Serializer):
    file = AudioFileField(allow_empty_file=False, max_length=255)
    language = serializers.RegexField(
        r'^[A-Za-z]{2,3}$', required=False, allow_blank=True, max_length=3,
        help_text='Optional ISO-639 language code, for example zh or en.',
    )

    def validate_file(self, value):
        maximum = getattr(settings, 'CHAT_AI_STT_MAX_FILE_SIZE', 10 * 1024 * 1024)
        if value.size > maximum:
            raise AudioFileTooLarge(
                f'Audio file exceeds the {maximum // 1024 // 1024} MiB limit.'
            )
        suffix = Path(value.name or '').suffix.lower()
        if suffix not in AUDIO_CONTENT_TYPES:
            raise serializers.ValidationError(
                'Unsupported audio format. Use flac, m4a, mp3, mp4, mpeg, mpga, ogg, wav, or webm.'
            )
        return value

    @staticmethod
    def validate_language(value):
        return value.lower()


class TranscriptionResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    language = serializers.CharField(allow_blank=True)


class SpeechModelUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Speech-to-text model is unavailable.'
    default_code = 'speech_model_unavailable'


class InvalidAudio(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Audio could not be transcribed.'
    default_code = 'invalid_audio'


class SpeechModelTimeout(APIException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = 'Speech-to-text request timed out.'
    default_code = 'speech_model_timeout'


class SpeechModelRateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Speech-to-text provider rate limit was exceeded.'
    default_code = 'speech_model_rate_limited'


class TranscriptionFailed(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'Audio could not be transcribed.'
    default_code = 'transcription_failed'


class TranscriptionAutoSchema(CustomAutoSchema):
    def map_parsers(self):
        return ['multipart/form-data']


def _probe_audio_duration(uploaded_file, suffix):
    maximum = max(0, getattr(settings, 'CHAT_AI_STT_MAX_DURATION', 120))
    if maximum == 0:
        return
    configured_binary = getattr(settings, 'CHAT_AI_STT_FFPROBE_BIN', 'ffprobe')
    binary = shutil.which(configured_binary)
    if not binary:
        raise AudioInspectionUnavailable('ffprobe is required when CHAT_AI_STT_MAX_DURATION is enabled.')

    temporary = None
    try:
        try:
            source_path = uploaded_file.temporary_file_path()
        except (AttributeError, TypeError):
            temporary = tempfile.NamedTemporaryFile(suffix=suffix)
            uploaded_file.seek(0)
            shutil.copyfileobj(uploaded_file, temporary)
            temporary.flush()
            source_path = temporary.name
        completed = subprocess.run(
            [
                binary, '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', source_path,
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        try:
            duration = float(completed.stdout.strip())
        except (TypeError, ValueError):
            duration = 0
        if completed.returncode != 0 or not math.isfinite(duration) or duration <= 0:
            raise InvalidAudio('Audio duration could not be determined.')
        if duration > maximum:
            raise AudioTooLong(f'Audio duration exceeds the {maximum} second limit.')
    except subprocess.TimeoutExpired as exc:
        raise InvalidAudio('Audio inspection timed out.') from exc
    except OSError as exc:
        raise AudioInspectionUnavailable('ffprobe could not be executed.') from exc
    finally:
        uploaded_file.seek(0)
        if temporary is not None:
            temporary.close()


class TranscriptionView(APIView):
    schema = TranscriptionAutoSchema()
    permission_classes = (
        ChatAIServicePermission, IsValidUser, ChatAIOrgPermission, CanUseChatAI,
    )
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = (TranscriptionThrottle,)

    @extend_schema(
        request=TranscriptionRequestSerializer,
        responses={
            200: TranscriptionResponseSerializer,
            400: OpenApiResponse(description='Invalid audio file or language code'),
            413: OpenApiResponse(description='Audio file exceeds the configured size limit'),
            429: OpenApiResponse(description='Request or provider rate limit exceeded'),
            502: OpenApiResponse(description='Speech-to-text provider failed'),
            503: OpenApiResponse(description='Speech-to-text is disabled or unavailable'),
            504: OpenApiResponse(description='Speech-to-text request timed out'),
        },
    )
    def post(self, request):
        maximum = getattr(settings, 'CHAT_AI_STT_MAX_FILE_SIZE', 10 * 1024 * 1024)
        try:
            content_length = int(request.META.get('CONTENT_LENGTH') or 0)
        except (TypeError, ValueError):
            content_length = 0
        if content_length > maximum + 1024 * 1024:
            raise AudioFileTooLarge()

        concurrency = TranscriptionConcurrency(request.user.pk)
        try:
            acquired = concurrency.acquire()
        except Exception as exc:
            raise TranscriptionCapacityUnavailable() from exc
        if not acquired:
            raise TranscriptionBusy()
        uploaded_file = None
        try:
            serializer = TranscriptionRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            uploaded_file = serializer.validated_data['file']
            suffix = Path(uploaded_file.name).suffix.lower()
            _probe_audio_duration(uploaded_file, suffix)
            provider = get_transcription_provider()
            result = async_to_sync(provider.transcribe)(
                file=uploaded_file.file,
                filename=f'audio{suffix}',
                content_type=AUDIO_CONTENT_TYPES[suffix],
                language=serializer.validated_data.get('language', ''),
            )
        except SpeechToTextInputError as exc:
            raise InvalidAudio() from exc
        except SpeechToTextTimeoutError as exc:
            raise SpeechModelTimeout() from exc
        except SpeechToTextRateLimitError as exc:
            raise SpeechModelRateLimited() from exc
        except SpeechToTextConfigurationError as exc:
            raise SpeechModelUnavailable() from exc
        except SpeechToTextError as exc:
            raise TranscriptionFailed() from exc
        finally:
            if uploaded_file is not None:
                uploaded_file.close()
            concurrency.release()
        return Response(TranscriptionResponseSerializer(result).data)
