import mimetypes
from pathlib import Path

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from chat_ai.assistants import ASSISTANTS, is_assistant_available
from chat_ai.executor.sanitizer import sanitize_text, summarize
from chat_ai.file_extractor import FileExtractionError, extract_file_text
from chat_ai.models import (
    Approval, Conversation, Message, MessageFile, MessageImage,
)


SUPPORTED_IMAGE_TYPES = {'image/gif', 'image/jpeg', 'image/png', 'image/webp'}


class MessageImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MessageImage
        fields = ('id', 'name', 'content_type', 'size', 'url')
        read_only_fields = fields

    @staticmethod
    def get_url(instance):
        return (
            f'/api/v1/chat-ai/conversations/{instance.message.conversation_id}/'
            f'messages/{instance.message_id}/images/{instance.id}/'
        )


class MessageFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MessageFile
        fields = ('id', 'name', 'content_type', 'size', 'url')
        read_only_fields = fields

    @staticmethod
    def get_url(instance):
        return (
            f'/api/v1/chat-ai/conversations/{instance.message.conversation_id}/'
            f'messages/{instance.message_id}/files/{instance.id}/'
        )


class ConversationSerializer(serializers.ModelSerializer):
    def validate_title(self, value):
        if sanitize_text(value) != value:
            raise serializers.ValidationError('Sensitive credentials cannot be stored in a conversation title.')
        return value

    def validate_assistant(self, value):
        if value not in ASSISTANTS:
            raise serializers.ValidationError('Unknown Chat AI assistant.')
        request = self.context.get('request')
        if not request or not is_assistant_available(value, request.user):
            raise serializers.ValidationError(
                'You do not have permission to use this Chat AI assistant.'
            )
        return value

    class Meta:
        model = Conversation
        fields = ('id', 'title', 'assistant', 'model', 'status', 'date_created', 'date_updated')
        read_only_fields = ('id', 'model', 'status', 'date_created', 'date_updated')


class MessageSerializer(serializers.ModelSerializer):
    images = MessageImageSerializer(many=True, read_only=True)
    files = MessageFileSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = (
            'id', 'role', 'content', 'status', 'model', 'input_tokens',
            'output_tokens', 'error', 'images', 'files', 'result_cards',
            'regenerated_from', 'date_created',
        )
        read_only_fields = fields


class ConversationAuditAttachmentSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    content_type = serializers.CharField(read_only=True)
    size = serializers.IntegerField(read_only=True)


class ConversationAuditMessageSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()
    images = ConversationAuditAttachmentSerializer(many=True, read_only=True)
    files = ConversationAuditAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = (
            'id', 'role', 'content', 'status', 'model', 'input_tokens',
            'output_tokens', 'error', 'images', 'files', 'date_created',
        )
        read_only_fields = fields

    @staticmethod
    def get_content(instance):
        return sanitize_text(instance.content)

    @staticmethod
    def get_error(instance):
        return sanitize_text(instance.error)


class ConversationAuditListSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    last_question_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Conversation
        fields = (
            'id', 'title', 'assistant', 'model', 'status', 'user',
            'message_count', 'question_count', 'last_question_at',
            'date_created', 'date_updated',
        )
        read_only_fields = fields

    @staticmethod
    def get_user(instance):
        return {
            'id': str(instance.user_id),
            'name': instance.user.name,
            'username': instance.user.username,
        }


class ConversationAuditDetailSerializer(ConversationAuditListSerializer):
    messages = serializers.SerializerMethodField()

    class Meta(ConversationAuditListSerializer.Meta):
        fields = ConversationAuditListSerializer.Meta.fields + ('messages',)

    @staticmethod
    def get_messages(instance):
        messages = getattr(instance, 'audit_messages', ())
        return ConversationAuditMessageSerializer(messages, many=True).data


class StreamMessageSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=32000, trim_whitespace=False, allow_blank=True,
        required=False, default='',
    )
    images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, max_length=255),
        allow_empty=False, required=False,
    )
    files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False, max_length=255),
        allow_empty=False, required=False,
    )
    web_search = serializers.BooleanField(required=False, default=False)

    def validate_content(self, value):
        if sanitize_text(value) != value:
            raise serializers.ValidationError(
                'Sensitive credentials cannot be sent to Chat AI. Submit them through a secure Core form.'
            )
        return value

    def validate_images(self, images):
        maximum_count = getattr(settings, 'CHAT_AI_IMAGE_MAX_COUNT', 4)
        maximum_file_size = getattr(settings, 'CHAT_AI_IMAGE_MAX_FILE_SIZE', 5 * 1024 * 1024)
        maximum_total_size = getattr(settings, 'CHAT_AI_IMAGE_MAX_TOTAL_SIZE', 10 * 1024 * 1024)
        if len(images) > maximum_count:
            raise serializers.ValidationError(f'No more than {maximum_count} images may be attached.')
        if sum(image.size for image in images) > maximum_total_size:
            raise serializers.ValidationError('The combined image size exceeds the configured limit.')
        for uploaded in images:
            uploaded.name = Path(str(uploaded.name).replace('\\', '/')).name[:255] or 'image'
            if uploaded.size > maximum_file_size:
                raise serializers.ValidationError(
                    f'Image {uploaded.name} exceeds the configured size limit.'
                )
            if uploaded.content_type not in SUPPORTED_IMAGE_TYPES:
                raise serializers.ValidationError(
                    'Unsupported image format. Use JPEG, PNG, WebP, or GIF.'
                )
            try:
                with Image.open(uploaded) as image:
                    actual_content_type = Image.MIME.get(image.format)
                    if actual_content_type not in SUPPORTED_IMAGE_TYPES:
                        raise serializers.ValidationError(
                            'Unsupported image format. Use JPEG, PNG, WebP, or GIF.'
                        )
                    if image.width * image.height > 25_000_000:
                        raise serializers.ValidationError('Image dimensions are too large.')
                    if getattr(image, 'is_animated', False):
                        raise serializers.ValidationError('Animated images are not supported.')
                    image.verify()
            except (Image.DecompressionBombError, OSError, UnidentifiedImageError) as exc:
                raise serializers.ValidationError(f'Image {uploaded.name} is invalid.') from exc
            finally:
                uploaded.seek(0)
            uploaded.content_type = actual_content_type
        return images
    def validate_files(self, files):
        maximum_count = getattr(settings, 'CHAT_AI_FILE_MAX_COUNT', 4)
        maximum_file_size = getattr(settings, 'CHAT_AI_FILE_MAX_FILE_SIZE', 10 * 1024 * 1024)
        maximum_total_size = getattr(settings, 'CHAT_AI_FILE_MAX_TOTAL_SIZE', 20 * 1024 * 1024)
        maximum_extracted_chars = getattr(settings, 'CHAT_AI_FILE_MAX_EXTRACTED_CHARS', 40000)
        maximum_total_extracted_chars = getattr(
            settings, 'CHAT_AI_FILE_MAX_TOTAL_EXTRACTED_CHARS', 80000
        )
        if len(files) > maximum_count:
            raise serializers.ValidationError(f'No more than {maximum_count} files may be attached.')
        if sum(uploaded.size for uploaded in files) > maximum_total_size:
            raise serializers.ValidationError('The combined file size exceeds the configured limit.')

        extracted_chars = 0
        for uploaded in files:
            uploaded.name = Path(str(uploaded.name).replace('\\', '/')).name[:255] or 'file'
            if sanitize_text(uploaded.name) != uploaded.name:
                raise serializers.ValidationError(
                    f'File name {uploaded.name} contains sensitive credentials.'
                )
            if uploaded.size > maximum_file_size:
                raise serializers.ValidationError(
                    f'File {uploaded.name} exceeds the configured size limit.'
                )
            remaining_chars = maximum_total_extracted_chars - extracted_chars
            if remaining_chars <= 0:
                raise serializers.ValidationError('The attached files contain too much text.')
            try:
                extracted_text = extract_file_text(
                    uploaded,
                    max_chars=min(maximum_extracted_chars, remaining_chars),
                )
            except FileExtractionError as exc:
                raise serializers.ValidationError(str(exc)) from exc
            if sanitize_text(extracted_text) != extracted_text:
                raise serializers.ValidationError(
                    f'File {uploaded.name} contains sensitive credentials and cannot be sent to Chat AI.'
                )
            extracted_chars += len(extracted_text)
            uploaded._chat_ai_extracted_text = extracted_text
            uploaded.content_type = (
                mimetypes.guess_type(uploaded.name)[0]
                or uploaded.content_type
                or 'application/octet-stream'
            )[:128]
        return files

    def validate_web_search(self, value):
        if value and not getattr(settings, 'CHAT_AI_WEB_SEARCH_ENABLED', False):
            raise serializers.ValidationError('Web search is disabled by the administrator.')
        return value

    def validate(self, attrs):
        if not attrs.get('content', '').strip() and not attrs.get('images') and not attrs.get('files'):
            raise serializers.ValidationError('Message content or an attachment is required.')
        return attrs


class BranchMessageSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=32000, trim_whitespace=False, allow_blank=True,
    )
    web_search = serializers.BooleanField(required=False, default=False)

    def validate_content(self, value):
        if sanitize_text(value) != value:
            raise serializers.ValidationError(
                'Sensitive credentials cannot be sent to Chat AI. Submit them through a secure Core form.'
            )
        return value

    def validate_web_search(self, value):
        if value and not getattr(settings, 'CHAT_AI_WEB_SEARCH_ENABLED', False):
            raise serializers.ValidationError('Web search is disabled by the administrator.')
        return value


class BackgroundMessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=32000, trim_whitespace=False)
    web_search = serializers.BooleanField(required=False, default=False)
    notify = serializers.BooleanField(required=False, default=True)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError('Message content is required.')
        if sanitize_text(value) != value:
            raise serializers.ValidationError(
                'Sensitive credentials cannot be sent to Chat AI.'
            )
        return value

    def validate_web_search(self, value):
        if value and not getattr(settings, 'CHAT_AI_WEB_SEARCH_ENABLED', False):
            raise serializers.ValidationError('Web search is disabled by the administrator.')
        return value


class RegenerateMessageSerializer(serializers.Serializer):
    web_search = serializers.BooleanField(required=False, default=False)

    def validate_web_search(self, value):
        if value and not getattr(settings, 'CHAT_AI_WEB_SEARCH_ENABLED', False):
            raise serializers.ValidationError('Web search is disabled by the administrator.')
        return value


class ApprovalSerializer(serializers.ModelSerializer):
    preview = serializers.SerializerMethodField()

    class Meta:
        model = Approval
        fields = (
            'id', 'conversation', 'operation_id', 'method', 'path', 'risk_level',
            'status', 'preview', 'result_summary', 'confirmed_at', 'expires_at',
            'error', 'date_created',
        )
        read_only_fields = fields

    @staticmethod
    def get_preview(instance):
        return summarize(instance.request_payload)


class OpenAPIRegistrySerializer(serializers.Serializer):
    schema_hash = serializers.CharField()
    schema_version = serializers.CharField()
    operation_count = serializers.IntegerField()
    refreshed_at = serializers.DateTimeField()
