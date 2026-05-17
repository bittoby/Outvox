"""
CSV Parser Utility for Lead Import
Supports multiple CSV formats and provides validation.

NO SMS SENDING - This is purely for parsing and validation.
"""

import csv
import io
from typing import List, Dict, Optional, Tuple
from .phone_validator import validate_us_phone_number


class CSVParseResult:
    """Result of CSV parsing operation."""
    
    def __init__(self):
        self.valid_leads: List[Dict] = []
        self.invalid_rows: List[Dict] = []
        self.duplicate_phones: List[str] = []
        self.errors: List[str] = []
        self.total_rows: int = 0
        self.valid_count: int = 0
        self.invalid_count: int = 0
        self.duplicate_count: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "valid_leads": self.valid_leads,
            "invalid_rows": [
                {
                    "row": row["row_number"],
                    "phone": row.get("phone", ""),
                    "error": row.get("error", "Unknown error")
                }
                for row in self.invalid_rows
            ],
            "duplicate_phones": self.duplicate_phones,
            "errors": self.errors,
            "summary": {
                "total_rows": self.total_rows,
                "valid_count": self.valid_count,
                "invalid_count": self.invalid_count,
                "duplicate_count": self.duplicate_count
            }
        }


def _clean(value: Optional[str]) -> str:
    """Clean CSV field value."""
    if value is None:
        return ""
    cleaned = value.strip()
    # Handle NULL values and empty strings
    if not cleaned or cleaned.upper() in ['NULL', 'N/A', 'NONE']:
        return ""
    # Remove surrounding quotes
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    return cleaned


def parse_csv_content(csv_content: str, existing_phones: Optional[set] = None) -> CSVParseResult:
    """
    Parse CSV content and validate leads.
    
    Supports two formats:
    1. Simple format: name,phone_number,Address,City,State,Zip
    2. Customer format: CustomerKey,FirstName,LastName,ResPhone,BusPhone,...
    
    Args:
        csv_content: Raw CSV content as string
        existing_phones: Set of existing phone numbers in database (for duplicate detection)
    
    Returns:
        CSVParseResult object with valid/invalid leads and statistics
    
    NO SMS IS SENT - This only parses and validates data.
    """
    result = CSVParseResult()
    existing_phones = existing_phones or set()
    seen_phones_in_csv = set()
    
    if not csv_content or not csv_content.strip():
        result.errors.append("CSV content is empty")
        return result
    
    try:
        # Try to parse CSV with csv.DictReader for better handling
        lines = csv_content.strip().split('\n')
        
        if len(lines) < 2:
            result.errors.append("CSV must have at least a header row and one data row")
            return result
        
        # Use csv module to handle quoted fields, commas in fields, etc.
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        headers = csv_reader.fieldnames
        
        if not headers:
            result.errors.append("Could not parse CSV headers")
            return result
        
        # Detect CSV format
        is_simple_format = 'phone_number' in headers
        is_customer_format = 'FirstName' in headers or 'ResPhone' in headers
        
        for row_number, row in enumerate(csv_reader, start=2):  # Start at 2 (after header)
            result.total_rows += 1
            
            try:
                # Extract fields based on format
                if is_simple_format:
                    lead = _parse_simple_format(row)
                elif is_customer_format:
                    lead = _parse_customer_format(row)
                else:
                    # Try to auto-detect from available fields
                    lead = _parse_auto_detect(row)
                
                if not lead:
                    result.invalid_rows.append({
                        "row_number": row_number,
                        "phone": "",
                        "error": "Could not extract required fields (name, phone_number)"
                    })
                    result.invalid_count += 1
                    continue
                
                # Validate phone number
                phone = lead.get('phone_number', '')
                is_valid, normalized, error = validate_us_phone_number(phone)
                
                if not is_valid:
                    result.invalid_rows.append({
                        "row_number": row_number,
                        "phone": phone,
                        "error": error or "Invalid phone number"
                    })
                    result.invalid_count += 1
                    continue
                
                # Update with normalized phone
                lead['phone_number'] = normalized
                
                # Check for duplicates in existing database
                if normalized in existing_phones:
                    result.duplicate_phones.append(normalized)
                    result.duplicate_count += 1
                    result.invalid_rows.append({
                        "row_number": row_number,
                        "phone": normalized,
                        "error": "Duplicate: Already exists in database"
                    })
                    continue
                
                # Check for duplicates within the CSV
                if normalized in seen_phones_in_csv:
                    result.duplicate_phones.append(normalized)
                    result.duplicate_count += 1
                    result.invalid_rows.append({
                        "row_number": row_number,
                        "phone": normalized,
                        "error": "Duplicate: Already in this CSV"
                    })
                    continue
                
                seen_phones_in_csv.add(normalized)
                
                # Set required fields for Milestone 3
                lead['sms_verified'] = False  # CRITICAL: NO SMS SENT YET
                lead['store_id'] = None  # Will be assigned in Milestone 4
                lead['dnc_flag'] = False
                lead['priority'] = lead.get('priority', 1)
                
                result.valid_leads.append(lead)
                result.valid_count += 1
                
            except Exception as e:
                result.invalid_rows.append({
                    "row_number": row_number,
                    "phone": "",
                    "error": f"Parse error: {str(e)}"
                })
                result.invalid_count += 1
    
    except Exception as e:
        result.errors.append(f"CSV parsing failed: {str(e)}")
    
    return result


def _parse_simple_format(row: Dict) -> Optional[Dict]:
    """Parse simple format: name,phone_number,Address,City,State,Zip"""
    name = _clean(row.get('name', ''))
    phone = _clean(row.get('phone_number', ''))
    
    if not phone:
        return None
    
    return {
        'name': name or "Unknown",
        'phone_number': phone,
        'Address': _clean(row.get('Address', '')),
        'City': _clean(row.get('City', '')),
        'County': _clean(row.get('County', '')),
        'State': _clean(row.get('State', '')),
        'Zip': _clean(row.get('Zip', ''))
    }


def _parse_customer_format(row: Dict) -> Optional[Dict]:
    """Parse customer format: FirstName,LastName,ResPhone,BusPhone,..."""
    first_name = _clean(row.get('FirstName', ''))
    last_name = _clean(row.get('LastName', ''))
    res_phone = _clean(row.get('ResPhone', ''))
    bus_phone = _clean(row.get('BusPhone', ''))
    
    # Prefer residential phone, fallback to business phone
    phone = res_phone or bus_phone
    
    if not phone:
        return None
    
    name = f"{first_name} {last_name}".strip()
    
    return {
        'name': name or "Unknown",
        'phone_number': phone,
        'Address': _clean(row.get('Address', '')),
        'City': _clean(row.get('City', '')),
        'County': _clean(row.get('County', '') or row.get('countyname', '')),
        'State': _clean(row.get('State', '')),
        'Zip': _clean(row.get('Zip', ''))
    }


def _parse_auto_detect(row: Dict) -> Optional[Dict]:
    """Auto-detect format from available fields."""
    # Try to find phone number field (case-insensitive)
    phone = None
    for key in row.keys():
        key_lower = key.lower()
        if 'phone' in key_lower:
            phone = _clean(row.get(key, ''))
            if phone:
                break
    
    if not phone:
        return None
    
    # Try to find name fields
    name = _clean(row.get('name', '') or row.get('Name', ''))
    if not name:
        first = _clean(row.get('FirstName', '') or row.get('first_name', ''))
        last = _clean(row.get('LastName', '') or row.get('last_name', ''))
        name = f"{first} {last}".strip()
    
    return {
        'name': name or "Unknown",
        'phone_number': phone,
        'Address': _clean(row.get('Address', '') or row.get('address', '')),
        'City': _clean(row.get('City', '') or row.get('city', '')),
        'County': _clean(row.get('County', '') or row.get('county', '') or row.get('countyname', '')),
        'State': _clean(row.get('State', '') or row.get('state', '')),
        'Zip': _clean(row.get('Zip', '') or row.get('zip', ''))
    }


# Test function
if __name__ == "__main__":
    print("CSV Parser - Test Cases")
    print("=" * 60)
    
    # Test simple format
    test_csv_simple = """name,phone_number,Address,City,State,Zip
John Doe,+15551234567,123 Main St,Anytown,CA,90001
Jane Smith,(555) 987-6543,456 Oak Ave,Othertown,CA,90002
Invalid User,123,789 Bad St,Faketown,CA,90003
Duplicate User,555-123-4567,999 Dup St,Anytown,CA,90001"""
    
    print("\n\nTest 1: Simple Format")
    print("-" * 60)
    result = parse_csv_content(test_csv_simple)
    print(f"Total rows: {result.total_rows}")
    print(f"Valid: {result.valid_count}")
    print(f"Invalid: {result.invalid_count}")
    print(f"\nValid leads:")
    for lead in result.valid_leads:
        print(f"  - {lead['name']}: {lead['phone_number']}")
    print(f"\nInvalid rows:")
    for invalid in result.invalid_rows:
        print(f"  - Row {invalid['row_number']}: {invalid['error']}")

