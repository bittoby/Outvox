from utils.phone_validator import (
    format_phone_display,
    normalize_phone_number,
    validate_us_phone_number,
)


def test_normalizes_common_us_phone_formats():
    assert normalize_phone_number("(555) 234-5678") == "+15552345678"
    assert normalize_phone_number("1-555-234-5678") == "+15552345678"


def test_validates_us_phone_number_to_e164():
    is_valid, normalized, error = validate_us_phone_number("+1 (555) 234-5678")

    assert is_valid is True
    assert normalized == "+15552345678"
    assert error is None


def test_rejects_invalid_area_and_exchange_codes():
    is_valid, normalized, error = validate_us_phone_number("155-123-4567")

    assert is_valid is False
    assert normalized is None
    assert "area code" in error.lower()


def test_formats_valid_phone_for_display():
    assert format_phone_display("+15552345678") == "(555) 234-5678"
