def bit(x):
    if x < 1:
        raise ValueError("x must be greater than 1")
    return 2 ** (x - 1)
