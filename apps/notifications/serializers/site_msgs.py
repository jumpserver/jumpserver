from bs4 import BeautifulSoup
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from common.utils import convert_html_to_markdown
from ..models import MessageContent


def _normalize_legacy_ticket_html(message):
    soup = BeautifulSoup(message or '', 'html.parser')
    container = soup.select_one('.ticket-container')
    if not container or container.select_one('ul.field-list'):
        return message

    cards = container.select('div.card')
    if not cards:
        return message

    title = container.select_one('h1.title')
    if title and getattr(title.find_next_sibling(), 'name', None) != 'hr':
        title.insert_after(soup.new_tag('hr'))

    for card in cards:
        field_groups = card.select('p.field-group')
        if not field_groups:
            continue

        field_list = soup.new_tag('ul', attrs={'class': 'field-list'})
        for group in field_groups:
            item = soup.new_tag('li', attrs={'class': 'field-group'})
            name = group.select_one('.field-name strong')
            value = group.select_one('.field-value')
            if name:
                name['class'] = 'field-name'
                item.append(name.extract())
            if value:
                item.append(' ')
                item.append(value.extract())
            field_list.append(item)

        field_groups[0].insert_before(field_list)
        for group in field_groups:
            group.decompose()

        if getattr(card.find_next_sibling(), 'name', None) != 'hr':
            card.insert_after(soup.new_tag('hr'))

    return str(soup)


class SenderMixin(ModelSerializer):
    sender = serializers.SerializerMethodField()

    def get_sender(self, site_msg) -> str:
        sender = site_msg.sender
        if sender:
            return str(sender)
        else:
            return ''


class MessageContentSerializer(SenderMixin, ModelSerializer):
    message = serializers.SerializerMethodField()

    class Meta:
        model = MessageContent
        fields = [
            'id', 'subject', 'message',
            'date_created', 'date_updated',
            'sender',
        ]

    @staticmethod
    def get_message(site_msg) -> str:
        message = _normalize_legacy_ticket_html(site_msg.message)
        markdown = convert_html_to_markdown(message)
        return markdown


class SiteMessageSerializer(SenderMixin, ModelSerializer):
    content = MessageContentSerializer(read_only=True)
    has_read = serializers.BooleanField(read_only=True)
    read_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = MessageContent
        fields = [
            'id', 'has_read', 'read_at', 'content', 'date_created'
        ]


class SiteMessageIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField())


class SiteMessageSendSerializer(serializers.Serializer):
    subject = serializers.CharField()
    message = serializers.CharField()
    display_mode = serializers.ChoiceField(
        choices=MessageContent.DisplayMode.choices, 
        default=MessageContent.DisplayMode.default
    )
    user_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    group_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    is_broadcast = serializers.BooleanField(default=False)
