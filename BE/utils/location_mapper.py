"""
Location Mapper - maps phone area codes to the nearest store location.

The data in this module is SAMPLE data for demonstration only. Replace
``STORE_LOCATIONS`` and ``AREA_CODE_MAP`` with the real locations and area
codes for your business before going to production. Consider externalising
them to a JSON file or a database table loaded at startup.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Sample store data
# ---------------------------------------------------------------------------
# Each entry is a single store. The ``google_maps`` field should point at the
# location's listing on a maps provider. The ``hours_*`` fields are free-form
# strings used directly in SMS bodies, so keep them human-readable.
#
# This is sample data — replace before production use.
# ---------------------------------------------------------------------------
STORE_LOCATIONS = {
    'downtown': {
        'name': 'DOWNTOWN',
        'db_name': 'DOWNTOWN',
        'address': '100 Main St, Anytown, USA 00001',
        'phone': '555-010-0001',
        'hours_weekdays': '10-6 Mon-Fri',
        'hours_saturday': '10-5 Saturday',
        'hours_sunday': 'Sunday closed',
        'google_maps': 'https://maps.google.com/?q=100+Main+St'
    },
    'uptown': {
        'name': 'UPTOWN',
        'db_name': 'UPTOWN',
        'address': '200 North Ave, Anytown, USA 00002',
        'phone': '555-010-0002',
        'hours_weekdays': '10-6 Mon-Fri',
        'hours_saturday': '10-5 Saturday',
        'hours_sunday': '10-5 Sunday',
        'google_maps': 'https://maps.google.com/?q=200+North+Ave'
    },
    'westside': {
        'name': 'WESTSIDE',
        'db_name': 'WESTSIDE',
        'address': '300 West Blvd, Anytown, USA 00003',
        'phone': '555-010-0003',
        'hours_weekdays': '9-5 Mon-Fri',
        'hours_saturday': '9-5 Saturday',
        'hours_sunday': 'Sunday closed',
        'google_maps': 'https://maps.google.com/?q=300+West+Blvd'
    },
}

# Sample area-code routing. Replace with the area codes you actually serve.
# Numbers from unmapped area codes will fall back to the first store in
# STORE_LOCATIONS (see ``get_closest_location``).
AREA_CODE_MAP = {
    '555': ['downtown', 'uptown', 'westside'],
}


def default_store_key() -> str:
    """Return the first configured store key. Used as the universal fallback."""
    if not STORE_LOCATIONS:
        raise RuntimeError("STORE_LOCATIONS is empty; configure at least one store.")
    return next(iter(STORE_LOCATIONS))


# Backwards-compatible alias (used by older imports inside this module).
_default_store_key = default_store_key


def get_area_code(phone_number: str) -> str:
    """Extract the 3-digit area code from a US phone number."""
    clean_number = (
        phone_number.replace('+', '')
        .replace('-', '')
        .replace(' ', '')
        .replace('(', '')
        .replace(')', '')
    )
    if clean_number.startswith('1'):
        clean_number = clean_number[1:]
    return clean_number[:3] if len(clean_number) >= 3 else ''


def get_closest_location(phone_number: str, shop_id: str = None):
    """
    Determine the closest store location based on phone number or shop_id.

    Args:
        phone_number: Customer's phone number.
        shop_id:      Optional store identifier from the lead row.

    Returns:
        dict: Location entry from ``STORE_LOCATIONS``.
    """
    default_key = _default_store_key()

    if shop_id:
        key = shop_id.lower().strip()
        # Direct match wins.
        if key in STORE_LOCATIONS:
            return STORE_LOCATIONS[key]
        # Fall back to default if shop_id is not configured.
        return STORE_LOCATIONS[default_key]

    area_code = get_area_code(phone_number)
    if area_code in AREA_CODE_MAP:
        possible_locations = AREA_CODE_MAP[area_code]
        if possible_locations:
            location_key = possible_locations[0]
            return STORE_LOCATIONS.get(location_key, STORE_LOCATIONS[default_key])

    return STORE_LOCATIONS[default_key]


def get_location_list_string() -> str:
    """Get a comma-separated list of store names for prompt context."""
    return ", ".join(store['name'] for store in STORE_LOCATIONS.values())


def format_sms_message(customer_name: str, location: dict) -> str:
    """Format a brand-neutral directions SMS for a single location."""
    try:
        from config import config
        company_name = config.brand.COMPANY_NAME
    except Exception:
        company_name = "Acme Pawn"

    return (
        f"Hi {customer_name}, thanks for speaking with us!\n\n"
        f"Visit {company_name} - {location['name']} at:\n"
        f"{location['address']}\n\n"
        f"Get directions: {location['google_maps']}\n\n"
        f"Hours: {location['hours_weekdays']}\n"
        f"{location['hours_saturday']}\n"
        f"{location['hours_sunday']}\n\n"
        "Bring your gold, jewelry, watches, or electronics for a FREE appraisal. "
        "Walk out with cash in minutes!\n\n"
        "Reply STOP to opt out."
    )


def detect_location_from_transcript(transcript: str) -> Optional[str]:
    """
    Detect which store a customer is referring to based on keywords.

    The keyword lists below are derived from the names and addresses of each
    configured store. Operators who add more stores should also extend the
    keyword lists with neighborhood names, street references, and other
    common identifiers their customers use.
    """
    if not transcript or not transcript.strip():
        return None

    transcript_lower = transcript.lower()

    location_keywords = {
        key: [
            store['name'].lower(),
            store['address'].split(',')[0].lower(),
        ]
        for key, store in STORE_LOCATIONS.items()
    }

    location_scores = {}
    for location_key, keywords in location_keywords.items():
        score = 0
        for keyword in keywords:
            if not keyword:
                continue
            count = transcript_lower.count(keyword)
            if count > 0:
                score += count
                # Slight bonus for street-name matches (they're more specific).
                if any(c.isdigit() for c in keyword):
                    score += 2
        if score > 0:
            location_scores[location_key] = score

    if location_scores:
        best_location = max(location_scores.items(), key=lambda x: x[1])
        return best_location[0]

    return None


def get_store_info(location_name: str) -> dict:
    """Look up a store by its display name or db_name (case-insensitive)."""
    default_key = _default_store_key()
    location_name_upper = (location_name or "").upper()

    for store in STORE_LOCATIONS.values():
        if store['name'] == location_name_upper or store.get('db_name') == location_name_upper:
            return store

    for store in STORE_LOCATIONS.values():
        if location_name_upper in store['name'] or location_name_upper in store.get('db_name', ''):
            return store

    return STORE_LOCATIONS[default_key]


def get_all_locations_summary() -> str:
    """Get a summary of all store locations for AI context."""
    return "\n".join(
        f"{loc['name']}: {loc['address']}" for loc in STORE_LOCATIONS.values()
    )


if __name__ == "__main__":
    # Quick sanity check using the sample area code.
    for phone in ["+15555550101", "+15555550102", "+19995550000"]:
        location = get_closest_location(phone)
        print(f"{phone} -> {location['name']}: {location['address']}")
