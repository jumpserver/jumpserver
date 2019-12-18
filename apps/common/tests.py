from django.test import TestCase

# Create your tests here.

from .utils import random_string, signer


def test_signer_len():
    results = {}
    for i in range(1, 4096):
        s = random_string(i)
        encs = signer.sign(s)
        results[i] = (len(encs)/len(s))
    results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    print(results)
