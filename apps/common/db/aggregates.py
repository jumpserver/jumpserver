from django.db.models import Aggregate


class GroupConcat(Aggregate):
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(expressions)s %(order_by)s %(separator)s)'
    allow_distinct = False

    def __init__(self, expression, order_by=None, separator=',', **extra):
        order_by_clause = ''
        if order_by is not None:
            order = 'ASC'
            prefix, body = order_by[1], order_by[1:]
            if prefix == '-':
                order = 'DESC'
            elif prefix == '+':
                pass
            else:
                body = order_by
            order_by_clause = f'ORDER BY {body} {order}'

        super().__init__(
            expression,
            order_by=order_by_clause,
            separator=f"SEPARATOR '{separator}'",
            **extra
        )
