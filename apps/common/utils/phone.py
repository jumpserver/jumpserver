import phonenumbers


def normalize_phone_number(value):
    if not isinstance(value, str) or not value:
        return value
    try:
        number = phonenumbers.parse(value, 'CN')
    except phonenumbers.NumberParseException:
        # Keep unparseable third-party values intact; API validation rejects them separately.
        return value
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
