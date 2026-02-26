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
        if self.piico_enable:
            try:
                result = self._device.sm3_hmac(key, data_bytes)
                return result.hex().upper()
            except Exception as e:
                logger.error('Compute SM3 HMAC error: %s', e)
                return ''
        try:
            result = hmac_module.new(key, msg=data_bytes, digestmod=hashlib.sha256)
            return result.hexdigest().upper()
        except Exception as e:
            logger.error('Compute SHA256 HMAC error: %s', e)
        return ''

    def compute_model_hmac(self, obj, fields) -> str:
        if isinstance(obj, dict):
            raw = ''.join(str(obj.get(f, '')) for f in fields)
        else:
            raw = ''.join(str(getattr(obj, f, '')) for f in fields)
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
            return {'encrypt_value': '', 'hmac_verify': None}

        computed = self.compute_model_hmac(obj, hmac_model.HMAC_FIELDS)
        return {
            'encrypt_value': stored,
            'hmac_verify': 'OK' if computed == stored else 'FAILED',
        }

    def verify_hmac(self, hmac_model, obj):
        return self.get_hmac_context(hmac_model, obj).get('hmac_verify')


hmac_handler = HmacHandler()
