# Copyright 2023 The GmSSL Project. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the License); you may
# not use this file except in compliance with the License.
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# GmSSL-Python - Python binding of the GmSSL library with `ctypes`

# =============================================================================
# This file is derived from GmSSL-Python project (v2.2.2)
# https://github.com/GmSSL/GmSSL-Python/blob/v2.2.2/gmssl.py
#
# The original project is licensed under the Apache License 2.0:
# http://www.apache.org/licenses/LICENSE-2.0
#
# Copyright 2023 The GmSSL Project. All Rights Reserved.
#
# Reason for inclusion:
# This file is included by direct copy due to dependency conflict issues
# when installing via pip (gmssl / gmssl-python naming conflict).
# No functional modifications have been made to the original source.
#
# Compliance:
# This file is used in accordance with the Apache License 2.0 terms.
# =============================================================================

from ctypes import *
from ctypes.util import find_library
import datetime
import sys

if find_library('gmssl') == None:
	raise ValueError('Install GmSSL dynamic library from https://github.com/guanzhi/GmSSL')
gmssl = cdll.LoadLibrary(find_library("gmssl"))
if gmssl.gmssl_version_num() < 30101:
	raise ValueError('GmSSL version < 3.1.1')

if sys.platform == 'win32':
	libc = cdll.LoadLibrary(find_library('msvcrt'))
else:
	libc = cdll.LoadLibrary(find_library('c'))


class NativeError(Exception):
	'''
	GmSSL libraray inner error
	'''

class StateError(Exception):
	'''
	Crypto state error
	'''

GMSSL_PYTHON_VERSION = "2.2.2"

def gmssl_library_version_num():
	return gmssl.gmssl_version_num()

def gmssl_library_version_str():
	gmssl.gmssl_version_str.restype = c_char_p
	return gmssl.gmssl_version_str().decode('ascii')

GMSSL_LIBRARY_VERSION = gmssl_library_version_str()


def rand_bytes(size):
	buf = create_string_buffer(size)
	gmssl.rand_bytes(buf, c_size_t(size))
	return buf.raw



SM3_DIGEST_SIZE = 32
_SM3_STATE_WORDS = 8
_SM3_BLOCK_SIZE = 64

class Sm3(Structure):

	_fields_ = [
		("dgst", c_uint32 * _SM3_STATE_WORDS),
		("nblocks", c_uint64),
		("block", c_uint8 * _SM3_BLOCK_SIZE),
		("num", c_size_t)
	]

	def __init__(self):
		gmssl.sm3_init(byref(self))

	def reset(self):
		gmssl.sm3_init(byref(self))

	def update(self, data):
		gmssl.sm3_update(byref(self), data, c_size_t(len(data)))

	def digest(self):
		dgst = create_string_buffer(SM3_DIGEST_SIZE)
		gmssl.sm3_finish(byref(self), dgst)
		return dgst.raw


SM3_HMAC_MIN_KEY_SIZE = 16
SM3_HMAC_MAX_KEY_SIZE = 64
SM3_HMAC_SIZE = SM3_DIGEST_SIZE

class Sm3Hmac(Structure):

	_fields_ = [
		("sm3_ctx", Sm3),
		("key", c_uint8 * _SM3_BLOCK_SIZE)
	]

	def __init__(self, key):
		if len(key) < SM3_HMAC_MIN_KEY_SIZE or len(key) > SM3_HMAC_MAX_KEY_SIZE:
			raise ValueError('Invalid SM3 HMAC key length')
		gmssl.sm3_hmac_init(byref(self), key, c_size_t(len(key)))

	def reset(self, key):
		if len(key) < SM3_HMAC_MIN_KEY_SIZE or len(key) > SM3_HMAC_MAX_KEY_SIZE:
			raise ValueError('Invalid SM3 HMAC key length')
		gmssl.sm3_hmac_init(byref(self), key, c_size_t(len(key)))

	def update(self, data):
		gmssl.sm3_hmac_update(byref(self), data, c_size_t(len(data)))

	def generate_mac(self):
		hmac = create_string_buffer(SM3_HMAC_SIZE)
		gmssl.sm3_hmac_finish(byref(self), hmac)
		return hmac.raw



SM3_PBKDF2_MIN_ITER = 10000		# from <gmssl/pbkdf2.h>
SM3_PBKDF2_MAX_ITER = 16777216		# 2^24
SM3_PBKDF2_MAX_SALT_SIZE = 64		# from <gmssl/pbkdf2.h>
SM3_PBKDF2_DEFAULT_SALT_SIZE = 8	# from <gmssl/pbkdf2.h>
SM3_PBKDF2_MAX_KEY_SIZE = 256		# from gmssljni.c:sm3_pbkdf2():sizeof(keybuf)

def sm3_pbkdf2(passwd, salt, iterator, keylen):

	if len(salt) > SM3_PBKDF2_MAX_SALT_SIZE:
		raise ValueError('Invalid salt length')

	if iterator < SM3_PBKDF2_MIN_ITER or iterator > SM3_PBKDF2_MAX_ITER:
		raise ValueError('Invalid iterator value')

	if keylen > SM3_PBKDF2_MAX_KEY_SIZE:
		raise ValueError('Invalid key length')

	passwd = passwd.encode('utf-8')
	key = create_string_buffer(keylen)

	if gmssl.pbkdf2_hmac_sm3_genkey(c_char_p(passwd), c_size_t(len(passwd)),
		salt, c_size_t(len(salt)), c_size_t(iterator), c_size_t(keylen), key) != 1:
		raise NativeError('libgmssl inner error')

	return key.raw



SM4_KEY_SIZE = 16
SM4_BLOCK_SIZE = 16
_SM4_NUM_ROUNDS = 32

class Sm4(Structure):

	_fields_ = [
		("rk", c_uint32 * _SM4_NUM_ROUNDS)
	]

	def __init__(self, key, encrypt):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if encrypt:
			gmssl.sm4_set_encrypt_key(byref(self), key)
		else:
			gmssl.sm4_set_decrypt_key(byref(self), key)

	def encrypt(self, block):
		if len(block) != SM4_BLOCK_SIZE:
			raise ValueError('Invalid block size')
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		gmssl.sm4_encrypt(byref(self), block, outbuf)
		return outbuf.raw


SM4_CBC_IV_SIZE = SM4_BLOCK_SIZE


class Sm4Cbc(Structure):

	_fields_ = [
		("sm4_key", Sm4),
		("iv", c_uint8 * SM4_BLOCK_SIZE),
		("block", c_uint8 * SM4_BLOCK_SIZE),
		("block_nbytes", c_size_t)
	]

	def __init__(self, key, iv, encrypt):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) != SM4_BLOCK_SIZE:
			raise ValueError('Invalid IV size')
		if encrypt == DO_ENCRYPT:
			if gmssl.sm4_cbc_encrypt_init(byref(self), key, iv) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm4_cbc_decrypt_init(byref(self), key, iv) != 1:
				raise NativeError('libgmssl inner error')
		self._encrypt = encrypt

	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if self._encrypt == DO_ENCRYPT:
			if gmssl.sm4_cbc_encrypt_update(byref(self), data, c_size_t(len(data)),
				outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm4_cbc_decrypt_update(byref(self), data, c_size_t(len(data)),
				outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if self._encrypt == True:
			if gmssl.sm4_cbc_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm4_cbc_decrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		return outbuf[:outlen.value]



SM4_CTR_IV_SIZE = 16


class Sm4Ctr(Structure):

	_fields_ = [
		("sm4_key", Sm4),
		("ctr", c_uint8 * SM4_BLOCK_SIZE),
		("block", c_uint8 * SM4_BLOCK_SIZE),
		("block_nbytes", c_size_t)
	]

	def __init__(self, key, iv):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) != SM4_BLOCK_SIZE:
			raise ValueError('Invalid IV size')
		if gmssl.sm4_ctr_encrypt_init(byref(self), key, iv) != 1:
			raise NativeError('libgmssl inner error')

	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.sm4_ctr_encrypt_update(byref(self), data, c_size_t(len(data)),
			outbuf, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.sm4_ctr_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return outbuf[:outlen.value]


ZUC_KEY_SIZE = 16
ZUC_IV_SIZE = 16

class ZucState(Structure):
	_fields_ = [
		("LFSR", c_uint32 * 16),
		("R1", c_uint32),
		("R2", c_uint32)
	]

class Zuc(Structure):

	_fields_ = [
		("zuc_state", ZucState),
		("block", c_uint8 * 4),
		("block_nbytes", c_size_t)
	]

	def __init__(self, key, iv):
		if len(key) != ZUC_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) != ZUC_IV_SIZE:
			raise ValueError('Invalid IV size')
		if gmssl.zuc_encrypt_init(byref(self), key, iv) != 1:
			raise NativeError('libgmssl inner error')

	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.zuc_encrypt_update(byref(self), data, c_size_t(len(data)),
			outbuf, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.zuc_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return outbuf[:outlen.value]


class gf128_t(Structure):
	_fields_ = [
		("hi", c_uint64),
		("lo", c_uint64)
	]


class Ghash(Structure):
	_fields_ = [
		("H", gf128_t),
		("X", gf128_t),
		("aadlen", c_size_t),
		("clen", c_size_t),
		("block", c_uint8 * 16),
		("num", c_size_t)
	]


SM4_GCM_MIN_IV_SIZE = 1
SM4_GCM_MAX_IV_SIZE = 64
SM4_GCM_DEFAULT_IV_SIZE = 12
SM4_GCM_DEFAULT_TAG_SIZE = 16
SM4_GCM_MAX_TAG_SIZE = 16

class Sm4Gcm(Structure):

	_fields_ = [
		("sm4_ctr_ctx", Sm4Ctr),
		("mac_ctx", Ghash),
		("Y", c_uint8 * 16),
		("taglen", c_size_t),
		("mac", c_uint8 * 16),
		("maclen", c_size_t)
	]

	def __init__(self, key, iv, aad, taglen = SM4_GCM_DEFAULT_TAG_SIZE, encrypt = True):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) < SM4_GCM_MIN_IV_SIZE or len(iv) > SM4_GCM_MAX_IV_SIZE:
			raise ValueError('Invalid IV size')
		if taglen < 1 or taglen > SM4_GCM_MAX_TAG_SIZE:
			raise ValueError('Invalid Tag length')
		if encrypt == DO_ENCRYPT:
			if gmssl.sm4_gcm_encrypt_init(byref(self), key, c_size_t(len(key)),
				iv, c_size_t(len(iv)), aad, c_size_t(len(aad)),
				c_size_t(taglen)) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm4_gcm_decrypt_init(byref(self), key, c_size_t(len(key)),
				iv, c_size_t(len(iv)), aad, c_size_t(len(aad)),
				c_size_t(taglen)) != 1:
				raise NativeError('libgmssl inner error')
		self._encrypt = encrypt

	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if self._encrypt == DO_ENCRYPT:
			if gmssl.sm4_gcm_encrypt_update(byref(self), data, c_size_t(len(data)),
				outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm4_gcm_decrypt_update(byref(self), data, c_size_t(len(data)),
				outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE + SM4_GCM_MAX_TAG_SIZE)
		outlen = c_size_t()
		if self._encrypt == DO_ENCRYPT:
			if gmssl.sm4_gcm_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm4_gcm_decrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise NativeError('libgmssl inner error')
		return outbuf[:outlen.value]


SM2_DEFAULT_ID = '1234567812345678'

SM2_MAX_SIGNATURE_SIZE = 72

SM2_MIN_PLAINTEXT_SIZE = 1
SM2_MAX_PLAINTEXT_SIZE = 255
SM2_MIN_CIPHERTEXT_SIZE = 45
SM2_MAX_CIPHERTEXT_SIZE = 366


class Sm2Point(Structure):
	_fields_ = [
		("x", c_uint8 * 32),
		("y", c_uint8 * 32)
	]


class Sm2Key(Structure):

	_fields_ = [
		("public_key", Sm2Point),
		("private_key", c_uint8 * 32)
	]

	def __init__(self):
		self._has_public_key = False
		self._has_private_key = False

	def generate_key(self):
		if gmssl.sm2_key_generate(byref(self)) != 1:
			raise NativeError('libgmssl inner error')
		self._has_public_key = True
		self._has_private_key = True

	def has_private_key(self):
		return self._has_private_key

	def has_public_key(self):
		return self._has_public_key

	def compute_z(self, signer_id = SM2_DEFAULT_ID):
		if self._has_public_key == False:
			raise TypeError('has no public key')
		signer_id = signer_id.encode('utf-8')
		z = create_string_buffer(SM3_DIGEST_SIZE)
		gmssl.sm2_compute_z(z, byref(self), c_char_p(signer_id), c_size_t(len(signer_id)))
		return z.raw

	def export_encrypted_private_key_info_pem(self, path, passwd):
		if self._has_private_key == False:
			raise TypeError('has no private key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm2_private_key_info_encrypt_to_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))

	def import_encrypted_private_key_info_pem(self, path, passwd):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm2_private_key_info_decrypt_from_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_public_key = True
		self._has_private_key = True

	def export_public_key_info_pem(self, path):
		if self._has_public_key == False:
			raise TypeError('has no public key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		if gmssl.sm2_public_key_info_to_pem(byref(self), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))

	def import_public_key_info_pem(self, path):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		if gmssl.sm2_public_key_info_from_pem(byref(self), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_public_key = True
		self._has_private_key = False

	def sign(self, dgst):
		if self._has_private_key == False:
			raise TypeError('has no private key')
		if len(dgst) != SM3_DIGEST_SIZE:
			raise ValueError('Invalid SM3 digest size')
		sig = create_string_buffer(SM2_MAX_SIGNATURE_SIZE)
		siglen = c_size_t()
		if gmssl.sm2_sign(byref(self), dgst, sig, byref(siglen)) != 1:
			raise NativeError('libgmssl inner error')
		return sig[:siglen.value]

	def verify(self, dgst, signature):
		if self._has_public_key == False:
			raise TypeError('has no public key')
		if len(dgst) != SM3_DIGEST_SIZE:
			raise ValueError('Invalid SM3 digest size')
		if gmssl.sm2_verify(byref(self), dgst, signature, c_size_t(len(signature))) != 1:
			return False
		return True

	def encrypt(self, data):
		if self._has_public_key == False:
			raise TypeError('has no public key')
		if len(data) > SM2_MAX_PLAINTEXT_SIZE:
			raise NativeError('libgmssl inner error')
		outbuf = create_string_buffer(SM2_MAX_CIPHERTEXT_SIZE)
		outlen = c_size_t()
		if gmssl.sm2_encrypt(byref(self), data, c_size_t(len(data)),
			outbuf, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return outbuf[:outlen.value]

	def decrypt(self, ciphertext):
		if self._has_private_key == False:
			raise TypeError('has no private key')
		outbuf = create_string_buffer(SM2_MAX_PLAINTEXT_SIZE)
		outlen = c_size_t()
		if gmssl.sm2_decrypt(byref(self), ciphertext, c_size_t(len(ciphertext))
			, outbuf, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return outbuf[:outlen.value]


DO_ENCRYPT = True
DO_DECRYPT = False
DO_SIGN = True
DO_VERIFY = False

class Sm2Signature(Structure):

	_fields_ = [
		("sm3_ctx", Sm3),
		("key", Sm2Key)
	]

	def __init__(self, sm2_key, signer_id = SM2_DEFAULT_ID, sign = DO_SIGN):
		signer_id = signer_id.encode('utf-8')
		if sign == DO_SIGN:
			if sm2_key.has_private_key() != True:
				raise NativeError('libgmssl inner error')
			if gmssl.sm2_sign_init(byref(self), byref(sm2_key),
				c_char_p(signer_id), c_size_t(len(signer_id))) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if sm2_key.has_public_key() != True:
				raise NativeError('libgmssl inner error')
			if gmssl.sm2_verify_init(byref(self), byref(sm2_key),
				c_char_p(signer_id), c_size_t(len(signer_id))) != 1:
				raise NativeError('libgmssl inner error')
		self._sign = sign

	def update(self, data):
		if self._sign == DO_SIGN:
			if gmssl.sm2_sign_update(byref(self), data, c_size_t(len(data))) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm2_verify_update(byref(self), data, c_size_t(len(data))) != 1:
				raise NativeError('libgmssl inner error')

	def sign(self):
		if self._sign != DO_SIGN:
			raise StateError('not sign state')
		sig = create_string_buffer(SM2_MAX_SIGNATURE_SIZE)
		siglen = c_size_t()
		if gmssl.sm2_sign_finish(byref(self), sig, byref(siglen)) != 1:
			raise NativeError('libgmssl inner error')
		return sig[:siglen.value]

	def verify(self, signature):
		if self._sign != DO_VERIFY:
			raise StateError('not verify state')
		if gmssl.sm2_verify_finish(byref(self), signature, c_size_t(len(signature))) != 1:
			return False
		return True


class sm9_bn_t(Structure):
	_fields_ = [
		("d", c_uint64 * 8)
	]

class sm9_fp2_t(Structure):
	_fields_ = [
		("d", sm9_bn_t * 2)
	]

class Sm9Point(Structure):
	_fields_ = [
		("X", sm9_bn_t),
		("Y", sm9_bn_t),
		("Z", sm9_bn_t)
	]

class Sm9TwistPoint(Structure):
	_fields_ = [
		("X", sm9_fp2_t),
		("Y", sm9_fp2_t),
		("Z", sm9_fp2_t)
	]


SM9_MAX_ID_SIZE	= 63
SM9_MAX_PLAINTEXT_SIZE = 255
SM9_MAX_CIPHERTEXT_SIZE = 367

class Sm9EncKey(Structure):
	_fields_ = [
		("Ppube", Sm9Point),
		("de", Sm9TwistPoint)
	]

	def __init__(self, owner_id):
		self._id = owner_id.encode('utf-8')
		self._has_private_key = False

	def get_id(self):
		return self._id;

	def has_private_key(self):
		return self._has_private_key

	def import_encrypted_private_key_info_pem(self, path, passwd):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_enc_key_info_decrypt_from_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_private_key = True

	def export_encrypted_private_key_info_pem(self, path, passwd):
		if self._has_private_key != True:
			raise TypeError('has no private key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_enc_key_info_encrypt_to_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))

	def decrypt(self, ciphertext):
		if self._has_private_key != True:
			raise TypeError('has no private key')
		plaintext = create_string_buffer(SM9_MAX_PLAINTEXT_SIZE)
		outlen = c_size_t()
		if gmssl.sm9_decrypt(byref(self), c_char_p(self._id), c_size_t(len(self._id)),
			ciphertext, c_size_t(len(ciphertext)), plaintext, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return plaintext[0:outlen.value]


class Sm9EncMasterKey(Structure):
	_fields_ = [
		("Ppube", Sm9Point),
		("ke", sm9_bn_t)
	]

	def __init__(self):
		self._has_public_key = False
		self._has_private_key = False

	def generate_master_key(self):
		if gmssl.sm9_enc_master_key_generate(byref(self)) != 1:
			raise NativeError('libgmssl inner error')
		self._has_public_key = True
		self._has_private_key = True

	def extract_key(self, identity):
		if self._has_private_key != True:
			raise TypeError('has no master key')
		key = Sm9EncKey(identity)
		identity = identity.encode('utf-8')
		if gmssl.sm9_enc_master_key_extract_key(byref(self),
			c_char_p(identity), c_size_t(len(identity)), byref(key)) != 1:
			raise NativeError('libgmssl inner error')
		key._has_public_key = True
		key._has_private_key = True
		return key

	def import_encrypted_master_key_info_pem(self, path, passwd):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_enc_master_key_info_decrypt_from_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_public_key = True
		self._has_private_key = True

	def export_encrypted_master_key_info_pem(self, path, passwd):
		if self._has_private_key != True:
			raise TypeError('has no master key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_enc_master_key_info_encrypt_to_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))

	def export_public_master_key_pem(self, path):
		if self._has_public_key != True:
			raise TypeError('has no public master key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		if gmssl.sm9_enc_master_public_key_to_pem(byref(self), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))

	def import_public_master_key_pem(self, path):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		if gmssl.sm9_enc_master_public_key_from_pem(byref(self), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_public_key = True
		self._has_private_key = False

	def encrypt(self, plaintext, to):
		if self._has_public_key != True:
			raise TypeError('has no public master key')
		to = to.encode('utf-8')
		ciphertext = create_string_buffer(SM9_MAX_CIPHERTEXT_SIZE)
		outlen = c_size_t()
		if gmssl.sm9_encrypt(byref(self), c_char_p(to), c_size_t(len(to)),
			plaintext, c_size_t(len(plaintext)), ciphertext, byref(outlen)) != 1:
			raise NativeError('libgmssl inner error')
		return ciphertext[0:outlen.value]


class Sm9SignKey(Structure):
	_fields_ = [
		("Ppubs", Sm9TwistPoint),
		("ds", Sm9Point)
	]

	def __init__(self, owner_id):
		self._id = owner_id.encode('utf-8')
		self._has_private_key = False

	def get_id(self):
		return self._id;

	def has_private_key(self):
		return self._has_private_key

	def import_encrypted_private_key_info_pem(self, path, passwd):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_sign_key_info_decrypt_from_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_private_key = True

	def export_encrypted_private_key_info_pem(self, path, passwd):
		if self._has_private_key == False:
			raise TypeError('has no master key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_sign_key_info_encrypt_to_pem(byref(self), c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))


class Sm9SignMasterKey(Structure):
	_fields_ = [
		("Ppubs", Sm9TwistPoint),
		("ks", sm9_bn_t)
	]

	def __init__(self):
		self._has_public_key = False
		self._has_private_key = False

	def generate_master_key(self):
		if gmssl.sm9_sign_master_key_generate(byref(self)) != 1:
			raise NativeError('libgmssl inner error')
		self._has_public_key = True
		self._has_private_key = True

	def extract_key(self, identity):
		if self._has_private_key != True:
			raise TypeError('has no master key')
		key = Sm9SignKey(identity)
		identity = identity.encode('utf-8')
		if gmssl.sm9_sign_master_key_extract_key(byref(self),
			c_char_p(identity), c_size_t(len(identity)), byref(key)) != 1:
			raise NativeError('libgmssl inner error')
		key._has_public_key = True
		key._has_private_key = True
		return key

	def import_encrypted_master_key_info_pem(self, path, passwd):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_sign_master_key_info_decrypt_from_pem(byref(self),
			c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_public_key = True
		self._has_private_key = True

	def export_encrypted_master_key_info_pem(self, path, passwd):
		if self._has_private_key != True:
			raise TypeError('has no master key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		passwd = passwd.encode('utf-8')
		if gmssl.sm9_sign_master_key_info_encrypt_to_pem(byref(self),
			c_char_p(passwd), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))

	def export_public_master_key_pem(self, path):
		if self._has_public_key != True:
			raise TypeError('has no public master key')
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		if gmssl.sm9_sign_master_public_key_to_pem(byref(self), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))

	def import_public_master_key_pem(self, path):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'rb')
		if gmssl.sm9_sign_master_public_key_from_pem(byref(self), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		self._has_public_key = True
		self._has_private_key = False


SM9_SIGNATURE_SIZE = 104

class Sm9Signature(Structure):

	_fields_ = [
		("sm3", Sm3)
	]

	def __init__(self, sign = DO_SIGN):
		if sign == DO_SIGN:
			if gmssl.sm9_sign_init(byref(self)) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm9_verify_init(byref(self)) != 1:
				raise NativeError('libgmssl inner error')
		self._sign = sign
		self._inited = True


	def reset(self):
		if self._inited != True:
			raise StateError('not initialized')

		if self._sign == DO_SIGN:
			if gmssl.sm9_sign_init(byref(self)) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm9_verify_init(byref(self)) != 1:
				raise NativeError('libgmssl inner error')

	def update(self, data):

		if self._inited != True:
			raise StateError('not initialized')

		if self._sign == DO_SIGN:
			if gmssl.sm9_sign_update(byref(self), data, c_size_t(len(data))) != 1:
				raise NativeError('libgmssl inner error')
		else:
			if gmssl.sm9_verify_update(byref(self), data, c_size_t(len(data))) != 1:
				raise NativeError('libgmssl inner error')


	def sign(self, sign_key):
		if self._inited != True:
			raise StateError('not initialized')
		if self._sign != DO_SIGN:
			raise StateError('not sign state')

		sig = create_string_buffer(SM9_SIGNATURE_SIZE)
		siglen = c_size_t()
		if gmssl.sm9_sign_finish(byref(self), byref(sign_key), sig, byref(siglen)) != 1:
			raise NativeError('libgmssl inner error')
		return sig[:siglen.value]

	def verify(self, signature, public_master_key, signer_id):
		if self._inited != True:
			raise StateError('not initialized')
		if self._sign != DO_VERIFY:
			raise StateError('not verify state')

		signer_id = signer_id.encode('utf-8')

		if gmssl.sm9_verify_finish(byref(self), signature, c_size_t(len(signature)),
			byref(public_master_key), c_char_p(signer_id), c_size_t(len(signer_id))) != 1:
			return False
		return True



_ASN1_TAG_IA5String = 22
_ASN1_TAG_SEQUENCE = 0x30
_ASN1_TAG_SET = 0x31



def gmssl_parse_attr_type_and_value(name, d, dlen):
	oid = c_int()
	tag = c_int()
	val = c_void_p()
	vlen = c_size_t()

	if gmssl.x509_name_type_from_der(byref(oid), byref(d), byref(dlen)) != 1:
		raise NativeError('libgmssl inner error')
	gmssl.x509_name_type_name.restype = c_char_p
	oid_name = gmssl.x509_name_type_name(oid).decode('ascii')

	if oid_name == 'emailAddress':
		if gmssl.asn1_ia5_string_from_der_ex(_ASN1_TAG_IA5String, byref(val), byref(vlen), byref(d), byref(dlen)) != 1:
			raise NativeError('libgmssl inner error')
	else:
		if gmssl.x509_directory_name_from_der(byref(tag), byref(val), byref(vlen), byref(d), byref(dlen)) != 1:
			raise NativeError('libgmssl inner error')

	if dlen.value != 0:
		raise ValueError('invalid der encoding')

	value = create_string_buffer(vlen.value)
	libc.memcpy(value, val, vlen)

	name[oid_name] = value.raw.decode('utf-8')
	return True

def gmssl_parse_rdn(name, d, dlen):
	v = c_void_p()
	vlen = c_size_t()

	while dlen.value > 0:
		if gmssl.asn1_type_from_der(_ASN1_TAG_SEQUENCE, byref(v), byref(vlen), byref(d), byref(dlen)) != 1:
			raise NativeError('libgmssl inner error')

		if gmssl_parse_attr_type_and_value(name, v, vlen) != 1:
			raise NativeError('libgmssl inner error')

	return True

# https://stacktuts.com/how-to-correctly-pass-pointer-to-pointer-into-dll-in-python-and-ctypes#
def gmssl_parse_name(name, d, dlen):
	v = c_void_p()
	vlen = c_size_t()

	while dlen.value > 0:
		if gmssl.asn1_nonempty_type_from_der(c_int(_ASN1_TAG_SET), byref(v), byref(vlen), byref(d), byref(dlen)) != 1:
			raise NativeError('libgmssl inner error')
		gmssl_parse_rdn(name, v, vlen)
	return True


class Validity:

	def __init__(self, not_before, not_after):
		self.not_before = datetime.datetime.fromtimestamp(not_before)
		self.not_after = datetime.datetime.fromtimestamp(not_after)


class Sm2Certificate:

	def import_pem(self, path):

		cert = c_void_p()
		certlen = c_size_t()
		if gmssl.x509_cert_new_from_file(byref(cert), byref(certlen), path.encode('utf-8')) != 1:
			raise NativeError('libgmssl inner error')

		self._cert = create_string_buffer(certlen.value)
		libc.memcpy(self._cert, cert, certlen)
		libc.free(cert)

	def get_raw(self):
		return self._cert;

	def export_pem(self, path):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(path.encode('utf-8'), 'wb')
		if gmssl.x509_cert_to_pem(self._cert, c_size_t(len(self._cert)), c_void_p(fp)) != 1:
			raise NativeError('libgmssl inner error')

	def get_serial_number(self):

		serial_ptr = c_void_p()
		serial_len = c_size_t()

		if gmssl.x509_cert_get_issuer_and_serial_number(self._cert, c_size_t(len(self._cert)),
			None, None, byref(serial_ptr), byref(serial_len)) != 1:
			raise NativeError('libgmssl inner error')

		serial = create_string_buffer(serial_len.value)
		libc.memcpy(serial, serial_ptr, serial_len)
		return serial.raw

	def get_issuer(self):
		issuer_ptr = c_void_p()
		issuer_len = c_size_t()
		if gmssl.x509_cert_get_issuer(self._cert, c_size_t(len(self._cert)),
			byref(issuer_ptr), byref(issuer_len)) != 1:
			raise NativeError('libgmssl inner error')
		issuer_raw = create_string_buffer(issuer_len.value)
		libc.memcpy(issuer_raw, issuer_ptr, issuer_len)

		issuer = { "raw_data" : issuer_raw.raw }
		gmssl_parse_name(issuer, issuer_ptr, issuer_len)
		return issuer

	def get_subject(self):
		subject_ptr = c_void_p()
		subject_len = c_size_t()
		if gmssl.x509_cert_get_subject(self._cert, c_size_t(len(self._cert)),
			byref(subject_ptr), byref(subject_len)) != 1:
			raise NativeError('libgmssl inner error')
		subject_raw = create_string_buffer(subject_len.value)
		libc.memcpy(subject_raw, subject_ptr, subject_len)

		subject = { "raw_data" : subject_raw.raw }
		gmssl_parse_name(subject, subject_ptr, subject_len)
		return subject

	def get_subject_public_key(self):
		public_key = Sm2Key()
		gmssl.x509_cert_get_subject_public_key(self._cert, c_size_t(len(self._cert)), byref(public_key))
		public_key._has_private_key = False
		public_key._has_public_key = True
		return public_key

	def get_validity(self):
		not_before = c_ulong()
		not_after = c_ulong()
		if gmssl.x509_cert_get_details(self._cert, c_size_t(len(self._cert)),
			None, None, None, None, None, None,
			byref(not_before), byref(not_after),
			None, None, None, None, None, None, None, None, None, None, None, None) != 1:
			raise NativeError('libgmssl inner error')
		return Validity(not_before.value, not_after.value)

	def verify_by_ca_certificate(self, cacert, sm2_id):

		cacert_raw = cacert.get_raw()
		sm2_id = sm2_id.encode('utf-8')

		if gmssl.x509_cert_verify_by_ca_cert(self._cert, c_size_t(len(self._cert)),
			cacert_raw, c_size_t(len(cacert_raw)), c_char_p(sm2_id), c_size_t(len(sm2_id))) != 1:
			return False
		return True

