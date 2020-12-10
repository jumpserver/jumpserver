import inspect


def copy_function_args(func, locals_dict: dict):
    signature = inspect.signature(func)
    keys = signature.parameters.keys()
    kwargs = {}
    for k in keys:
        kwargs[k] = locals_dict.get(k)
    return kwargs
