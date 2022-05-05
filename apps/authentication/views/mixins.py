# -*- coding: utf-8 -*-
#

class METAMixin:
    def get_next_url_from_meta(self):
        request_meta = self.request.META or {}
        next_url = None
        referer = request_meta.get('HTTP_REFERER', '')
        next_url_item = referer.rsplit('next=', 1)
        if len(next_url_item) > 1:
            next_url = next_url_item[-1]
        return next_url
