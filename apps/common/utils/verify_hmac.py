import hashlib
import hmac as hmac_module

from django.conf import settings

from common.utils import get_logger, lazyproperty

logger = get_logger(__file__)

__all__ = ['hmac_handler']


class HmacHandler:
    @lazyproperty
    def _device(self):
        from common.sdk.gm import piico
        return piico.open_piico_device()

    @property
    def enable(self):
        return getattr(settings, 'GMSSL_ENABLED', False)

    @property
    def piico_enable(self):
        return self.enable and getattr(settings, 'PIICO_DEVICE_ENABLE', False)

    def compute_hmac(self, data: str) -> str:
        if not self.enable:
            return ''
        key = settings.SECRET_KEY[:32].encode('utf-8')
        data_bytes = data.encode('utf-8')
        logger.debug('compute_hmac input data: %r (len=%d)', data[:200], len(data))
        if self.piico_enable:
            try:
                result = self._device.sm3_hmac(key, data_bytes)
                hmac_value = result.hex().upper()
                logger.debug('compute_hmac [SM3] result: %s', hmac_value)
                return hmac_value
            except Exception as e:
                logger.error('Compute SM3 HMAC error: %s', e)
                return ''
        try:
            result = hmac_module.new(key, msg=data_bytes, digestmod=hashlib.sha256)
            hmac_value = result.hexdigest().upper()
            logger.debug('compute_hmac [SHA256] result: %s', hmac_value)
            return hmac_value
        except Exception as e:
            logger.error('Compute SHA256 HMAC error: %s', e)
        return ''

    def compute_model_hmac(self, obj, fields) -> str:
        if isinstance(obj, dict):
            raw = ''.join(str(obj.get(f, '')) for f in fields)
        else:
            raw = ''.join(str(getattr(obj, f, '')) for f in fields)
        logger.debug(
            'compute_model_hmac obj=%s fields=%s raw=%r',
            type(obj).__name__, fields, raw[:200]
        )
        return self.compute_hmac(raw)

    def create_hmac_record(self, hmac_model, record_id, obj):
        if not self.enable:
            return
        hmac_value = self.compute_model_hmac(obj, hmac_model.HMAC_FIELDS)
        if not hmac_value:
            return
        try:
            hmac_model.objects.create(
                record_id=record_id,
                encrypt_fields=hmac_model.HMAC_FIELDS_STR,
                encrypt_value=hmac_value,
            )
        except Exception as e:
            logger.error('Create HMAC record error: %s', e)

    def update_hmac_record(self, hmac_model, record_id, obj):
        if not self.enable:
            return
        hmac_value = self.compute_model_hmac(obj, hmac_model.HMAC_FIELDS)
        if not hmac_value:
            return
        try:
            hmac_model.objects.filter(record_id=record_id).update(
                encrypt_value=hmac_value,
            )
        except Exception as e:
            logger.error('Update HMAC record error: %s', e)

    def bulk_create_hmac_records(self, hmac_model, records):
        if not self.enable:
            return
        hmac_records = []
        for obj in records:
            hmac_value = self.compute_model_hmac(obj, hmac_model.HMAC_FIELDS)
            if hmac_value:
                record_id = obj.get('id') if isinstance(obj, dict) else obj.id
                hmac_records.append(hmac_model(
                    record_id=record_id,
                    encrypt_fields=hmac_model.HMAC_FIELDS_STR,
                    encrypt_value=hmac_value,
                ))
        if hmac_records:
            try:
                hmac_model.objects.bulk_create(hmac_records)
            except Exception as e:
                logger.error('Bulk create HMAC records error: %s', e)

    def _get_stored_hmac(self, hmac_model, obj):
        """获取存储的 HMAC 值，返回 encrypt_value 字符串"""
        if isinstance(obj, dict):
            return obj.get('encrypt_value', '')

        # ES from_dict 对象会内嵌 encrypt_value；DB 对象需查 HMAC 表
        encrypt_value = getattr(obj, 'encrypt_value', None)
        if encrypt_value is not None:
            return encrypt_value

        try:
            hmac_record = hmac_model.objects.filter(record_id=obj.id).first()
        except Exception:
            return ''
        return hmac_record.encrypt_value if hmac_record else ''

    def get_hmac_context(self, hmac_model, obj):
        """返回 encrypt_value 和 hmac_verify，一次查询同时获取两个值"""
        if not self.enable:
            return {'encrypt_value': '', 'hmac_verify': None}

        stored = self._get_stored_hmac(hmac_model, obj)
        if not stored:
            logger.debug(
                'get_hmac_context no stored hmac for obj=%s (type=%s)',
                getattr(obj, 'id', obj.get('id', '?') if isinstance(obj, dict) else '?'),
                type(obj).__name__,
            )
            return {'encrypt_value': '', 'hmac_verify': None}

        computed = self.compute_model_hmac(obj, hmac_model.HMAC_FIELDS)
        verify = 'OK' if computed == stored else 'FAILED'
        if verify == 'FAILED':
            logger.warning(
                'HMAC verify FAILED for obj=%s (type=%s), '
                'stored=%s, computed=%s, fields=%s',
                getattr(obj, 'id', obj.get('id', '?') if isinstance(obj, dict) else '?'),
                type(obj).__name__, stored, computed, hmac_model.HMAC_FIELDS,
            )
        return {
            'encrypt_value': stored,
            'hmac_verify': verify,
        }

    def verify_hmac(self, hmac_model, obj):
        return self.get_hmac_context(hmac_model, obj).get('hmac_verify')


hmac_handler = HmacHandler()
