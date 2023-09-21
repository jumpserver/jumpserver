from rest_framework import renderers

from .csv import *
from .excel import *


class PassthroughRenderer(renderers.BaseRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = 'application/octet-stream'
    format = ''

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
