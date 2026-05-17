"""
Phone Number Validation Utility
Validates and normalizes US phone numbers to E.164 format.

NO SMS SENDING - This is purely for validation.
"""

import re
from typing import Tuple, Optional


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to E.164 format (+1XXXXXXXXXX).
    
    Accepts formats:
        - +15551234567
        - 15551234567
        - 5551234567
        - (555) 123-4567
        - 555-123-4567
        - 555.123.4567
    
    Returns normalized format: +15551234567
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Remove leading '1' if present (will be added back)
    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]
    
    # Ensure we have exactly 10 digits
    if len(digits) != 10:
        return ""
    
    # Return E.164 format
    return f"+1{digits}"


def validate_us_phone_number(phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate US phone number.
    
    Args:
        phone: Phone number string in any format
    
    Returns:
        Tuple of (is_valid, normalized_number, error_message)
        - is_valid: True if valid US phone number
        - normalized_number: E.164 format (+1XXXXXXXXXX) if valid, None otherwise
        - error_message: Error description if invalid, None otherwise
    
    Examples:
        >>> validate_us_phone_number("+15551234567")
        (True, "+15551234567", None)
        
        >>> validate_us_phone_number("invalid")
        (False, None, "Invalid phone number format")
    """
    if not phone or not isinstance(phone, str):
        return (False, None, "Phone number is required")
    
    # Remove all non-digit characters for validation
    digits = re.sub(r'\D', '', phone)
    
    # Check if starts with country code
    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]
    
    # Must be exactly 10 digits for US
    if len(digits) != 10:
        return (False, None, f"Invalid US phone number length: {len(digits)} digits (expected 10)")
    
    # Check for invalid patterns (all same digit, etc.)
    if len(set(digits)) == 1:
        return (False, None, "Phone number cannot be all same digits")
    
    # Check area code (first 3 digits) - cannot start with 0 or 1
    area_code = digits[:3]
    if area_code[0] in ['0', '1']:
        return (False, None, f"Invalid area code: {area_code} (cannot start with 0 or 1)")
    
    # Check exchange code (next 3 digits) - cannot start with 0 or 1
    exchange = digits[3:6]
    if exchange[0] in ['0', '1']:
        # Format phone for better error message: (XXX) XXX-XXXX
        formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        # Suggest a fix by changing first digit of exchange to 2
        suggested_exchange = '2' + exchange[1:]
        suggested_phone = f"({digits[:3]}) {suggested_exchange}-{digits[6:]}"
        return (False, None, f"Invalid exchange code: {exchange} (cannot start with 0 or 1). Phone: {formatted}. Suggested fix: {suggested_phone}")
    
    # Normalize to E.164 format
    normalized = f"+1{digits}"
    
    return (True, normalized, None)


def is_valid_us_phone(phone: str) -> bool:
    """
    Quick check if phone number is valid US format.
    
    Args:
        phone: Phone number string
    
    Returns:
        True if valid, False otherwise
    """
    is_valid, _, _ = validate_us_phone_number(phone)
    return is_valid


def format_phone_display(phone: str) -> str:
    """
    Format phone number for display: (555) 123-4567
    
    Args:
        phone: Phone number in any format
    
    Returns:
        Formatted phone number or original if invalid
    """
    is_valid, normalized, _ = validate_us_phone_number(phone)
    
    if not is_valid or not normalized:
        return phone
    
    # Remove +1 prefix
    digits = normalized[2:]
    
    # Format as (555) 123-4567
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


# Test function (for manual testing)
if __name__ == "__main__":
    print("Phone Number Validator - Test Cases")
    print("=" * 60)
    
    test_cases = [
        "+15552345678",  # Valid: exchange code 234 (starts with 2)
        "15552345678",
        "5552345678",
        "(555) 234-5678",  # Valid: exchange code 234
        "555-234-5678",
        "555.234.5678",
        "invalid",
        "123",
        "1111111111",  # All same digits
        "0551234567",  # Invalid area code
        "+1 (555) 234-5678",  # Valid: exchange code 234
        "",
        None
    ]
    
    for test in test_cases:
        is_valid, normalized, error = validate_us_phone_number(test)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"\n{status}: {test}")
        if is_valid:
            print(f"  Normalized: {normalized}")
            print(f"  Display: {format_phone_display(test)}")
        else:
            print(f"  Error: {error}")

