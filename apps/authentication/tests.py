from .utils import gen_key_pair, rsa_decrypt, rsa_encrypt


def test_rsa_encrypt_decrypt(message='test-password-$%^&*'):
    """ 测试加密/解密 """
    print('Need to encrypt message: {}'.format(message))
    rsa_private_key, rsa_public_key = gen_key_pair()
    print('RSA public key: \n{}'.format(rsa_public_key))
    print('RSA private key: \n{}'.format(rsa_private_key))
    message_encrypted = rsa_encrypt(message, rsa_public_key)
    print('Encrypted message: {}'.format(message_encrypted))
    message_decrypted = rsa_decrypt(message_encrypted, rsa_private_key)
    print('Decrypted message: {}'.format(message_decrypted))


