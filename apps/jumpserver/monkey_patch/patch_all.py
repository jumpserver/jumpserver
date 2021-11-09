from .model_iterable import patch_model_iterable

__all__ = ['patch', ]


def patch():
    patch_model_iterable()
