from rest_framework.pagination import LimitOffsetPagination, _positive_int


class JMSLimitOffsetPagination(LimitOffsetPagination):
    def get_limit(self, request):
        if self.limit_query_param:
            try:
                return _positive_int(
                    request.query_params[self.limit_query_param],
                    cutoff=self.max_limit
                )
            except (KeyError, ValueError):
                pass

        return self.default_limit
