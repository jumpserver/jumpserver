# -*- coding: utf-8 -*-
#


def jumpserver_processor(request):
    context = {}

    # Setting default pk
    context.update(
        {'DEFAULT_PK': '00000000-0000-0000-0000-000000000000'}
    )
    return context



