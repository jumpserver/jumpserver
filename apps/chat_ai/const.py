MAX_REVISION = 2 ** 63 - 1
MAX_RECORD_BYTES = 64 * 1024 * 1024
JOURNAL_RECORD_FIELDS = {'version', 'created_at', 'payload', 'checksum'}
