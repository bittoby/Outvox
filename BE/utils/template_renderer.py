#!/usr/bin/env python3
"""
SMS Template Renderer Utility
Renders SMS templates with dynamic placeholder substitution.

Usage:
    from utils.template_renderer import render_template, select_random_template
    
    template = "Hi {name}, this is {store_name}. Reply STOP to opt out."
    rendered = render_template(template, name="John", store_name="Acme Pawn")
    # Output: "Hi John, this is Acme Pawn. Reply STOP to opt out."
"""

import os
import random
import re
from typing import Dict, List, Optional


def render_template(template_text: str, **kwargs) -> str:
    """
    Render an SMS template with placeholder substitution.
    
    Args:
        template_text: Template string with placeholders like {name}, {store_name}
        **kwargs: Key-value pairs for placeholder substitution
    
    Returns:
        Rendered template string with placeholders replaced
    
    Example:
        >>> render_template("Hi {name}!", name="John")
        'Hi John!'
        
        >>> render_template("Visit {store_name} at {address}", 
        ...                 store_name="Store 1", address="123 Main St")
        'Visit Store 1 at 123 Main St'
    """
    rendered = template_text
    
    # Replace all placeholders with provided values
    for key, value in kwargs.items():
        placeholder = f"{{{key}}}"
        if placeholder in rendered:
            # Handle None values gracefully
            replacement = str(value) if value is not None else ""
            rendered = rendered.replace(placeholder, replacement)
    
    # Check for any remaining unreplaced placeholders and warn
    remaining_placeholders = re.findall(r'\{(\w+)\}', rendered)
    if remaining_placeholders:
        # Replace unreplaced placeholders with empty string (graceful degradation)
        for placeholder in remaining_placeholders:
            rendered = rendered.replace(f"{{{placeholder}}}", "")
    
    return rendered.strip()


def validate_template(template_text: str) -> Dict[str, any]:
    """
    Validate an SMS template for compliance and best practices.
    
    Args:
        template_text: Template string to validate
    
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "placeholders": List[str],
            "character_count": int
        }
    
    Validation Rules:
        - Must include "STOP" opt-out instruction
        - Should be under 160 characters (or 320 for longer messages)
        - Should include business identification
        - Placeholders must use valid format: {placeholder_name}
    """
    errors = []
    warnings = []
    
    # Extract placeholders
    placeholders = re.findall(r'\{(\w+)\}', template_text)
    
    # Check for STOP instruction (TCPA compliance)
    if 'STOP' not in template_text.upper():
        errors.append("Template must include 'STOP' opt-out instruction for TCPA compliance")
    
    # Check character count (after placeholder expansion estimate)
    # Estimate: assume average placeholder expands to 20 characters
    estimated_length = len(template_text)
    for placeholder in placeholders:
        placeholder_length = len(f"{{{placeholder}}}")
        estimated_length = estimated_length - placeholder_length + 20  # Estimate 20 chars
    
    if estimated_length > 320:
        warnings.append(f"Template may exceed 2 SMS segments (estimated {estimated_length} chars)")
    elif estimated_length > 160:
        warnings.append(f"Template will require 2 SMS segments (estimated {estimated_length} chars)")
    
    # Check for business identification.
    # We look for the configured company name (case-insensitive) or any of the
    # standard placeholders that the renderer can substitute.
    try:
        from config import config
        company_name = config.brand.COMPANY_NAME
    except Exception:
        company_name = os.getenv('COMPANY_NAME', 'Acme Pawn')

    identifiers = [
        company_name.lower(),
        '{store_name}',
        '{company_name}',
    ]
    has_business_id = any(keyword in template_text.lower() for keyword in identifiers)
    if not has_business_id:
        warnings.append("Template should include business identification (store/company name)")
    
    # Check for consent request
    has_consent_request = any(keyword in template_text.upper() for keyword in 
                              ['REPLY YES', 'TEXT YES', 'REPLY Y', 'TEXT BACK'])
    if not has_consent_request:
        warnings.append("Template should request explicit consent (e.g., 'Reply YES')")
    
    # Check for valid placeholder format
    invalid_placeholders = re.findall(r'\{[^a-zA-Z0-9_}]+\}', template_text)
    if invalid_placeholders:
        errors.append(f"Invalid placeholder format: {invalid_placeholders}. Use only alphanumeric and underscore.")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "placeholders": placeholders,
        "character_count": len(template_text),
        "estimated_length": estimated_length
    }


def select_random_template(templates: List[Dict], exclude_ids: Optional[List[int]] = None) -> Optional[Dict]:
    """
    Select a random template from a list of templates.
    
    Args:
        templates: List of template dictionaries with 'template_id' and 'template_text'
        exclude_ids: Optional list of template IDs to exclude from selection
    
    Returns:
        Randomly selected template dictionary, or None if no templates available
    
    Example:
        >>> templates = [
        ...     {"template_id": 1, "template_text": "Hi {name}!"},
        ...     {"template_id": 2, "template_text": "Hello {name}!"}
        ... ]
        >>> template = select_random_template(templates)
        >>> template['template_id'] in [1, 2]
        True
    """
    if not templates:
        return None
    
    # Filter out excluded templates
    if exclude_ids:
        templates = [t for t in templates if t.get('template_id') not in exclude_ids]
    
    if not templates:
        return None
    
    # Random selection with equal probability
    return random.choice(templates)


def get_template_placeholders(template_text: str) -> List[str]:
    """
    Extract all placeholder names from a template.
    
    Args:
        template_text: Template string
    
    Returns:
        List of placeholder names (without braces)
    
    Example:
        >>> get_template_placeholders("Hi {name}, visit {store_name}")
        ['name', 'store_name']
    """
    return re.findall(r'\{(\w+)\}', template_text)


def estimate_sms_segments(text: str) -> int:
    """
    Estimate the number of SMS segments required for a text message.
    
    Args:
        text: Message text
    
    Returns:
        Number of SMS segments (1-5+)
    
    Note:
        - Single segment: up to 160 characters (GSM-7 encoding)
        - Multi-segment: up to 153 characters per segment
        - This is a simplified estimation
    """
    length = len(text)
    
    if length <= 160:
        return 1
    elif length <= 306:  # 153 * 2
        return 2
    elif length <= 459:  # 153 * 3
        return 3
    elif length <= 612:  # 153 * 4
        return 4
    else:
        return 5


# Export functions
__all__ = [
    'render_template',
    'validate_template',
    'select_random_template',
    'get_template_placeholders',
    'estimate_sms_segments'
]

