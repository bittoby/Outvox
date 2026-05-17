"""
Language Validation Module
Detects and enforces English-only conversations.
"""

import re
from typing import Tuple


class LanguageValidator:
    """Validates that conversations are in English"""
    
    # Common non-English patterns
    SPANISH_PATTERNS = [
        r'\b(si|no|hola|gracias|por favor|buenos dias|buenas tardes)\b',
        r'\b(como estas|que tal|donde|cuando|porque)\b'
    ]
    
    RUSSIAN_PATTERNS = [
        r'[а-яА-ЯёЁ]{3,}',  # Cyrillic characters
    ]
    
    CHINESE_PATTERNS = [
        r'[\u4e00-\u9fff]{2,}',  # Chinese characters
    ]
    
    YIDDISH_HEBREW_PATTERNS = [
        r'[\u0590-\u05ff]{3,}',  # Hebrew characters
    ]
    
    def __init__(self):
        self.non_english_patterns = (
            self.SPANISH_PATTERNS +
            self.RUSSIAN_PATTERNS +
            self.CHINESE_PATTERNS +
            self.YIDDISH_HEBREW_PATTERNS
        )
    
    def is_english(self, text: str) -> Tuple[bool, str]:
        """
        Check if text is in English
        
        Args:
            text: Text to check
            
        Returns:
            Tuple[bool, str]: (is_english, detected_language)
        """
        if not text or not text.strip():
            return True, "unknown"
        
        text_lower = text.lower()
        
        # Check for Spanish
        for pattern in self.SPANISH_PATTERNS:
            if re.search(pattern, text_lower):
                return False, "spanish"
        
        # Check for Russian/Cyrillic
        for pattern in self.RUSSIAN_PATTERNS:
            if re.search(pattern, text):
                return False, "russian"
        
        # Check for Chinese
        for pattern in self.CHINESE_PATTERNS:
            if re.search(pattern, text):
                return False, "chinese"
        
        # Check for Hebrew/Yiddish
        for pattern in self.YIDDISH_HEBREW_PATTERNS:
            if re.search(pattern, text):
                return False, "hebrew"
        
        return True, "english"
    
    def get_language_switch_response(self, detected_language: str) -> str:
        """
        Get appropriate response when non-English is detected
        
        Args:
            detected_language: The detected language
            
        Returns:
            str: Polite response in English
        """
        responses = {
            "spanish": "I apologize, but I can only communicate in English. Do you speak English?",
            "russian": "I apologize, but I can only communicate in English. Do you speak English?",
            "chinese": "I apologize, but I can only communicate in English. Do you speak English?",
            "hebrew": "I apologize, but I can only communicate in English. Do you speak English?",
        }
        
        return responses.get(detected_language, 
                            "I apologize, but I can only communicate in English. Do you speak English?")
    
    def count_non_english_attempts(self) -> int:
        """Track number of non-English attempts in a call"""
        if not hasattr(self, '_non_english_count'):
            self._non_english_count = 0
        return self._non_english_count
    
    def increment_non_english_attempts(self) -> int:
        """Increment and return non-English attempt count"""
        if not hasattr(self, '_non_english_count'):
            self._non_english_count = 0
        self._non_english_count += 1
        return self._non_english_count
    
    def should_end_call_due_to_language(self, max_attempts: int = 2) -> bool:
        """
        Determine if call should end due to repeated non-English
        
        Args:
            max_attempts: Maximum number of non-English attempts before ending call
            
        Returns:
            bool: True if call should end
        """
        return self.count_non_english_attempts() >= max_attempts


# Global instance
_language_validator = None


def get_language_validator() -> LanguageValidator:
    """Get singleton instance of LanguageValidator"""
    global _language_validator
    if _language_validator is None:
        _language_validator = LanguageValidator()
    return _language_validator


# Convenience functions
def validate_language(text: str) -> Tuple[bool, str]:
    """Check if text is in English"""
    validator = get_language_validator()
    return validator.is_english(text)


def get_language_switch_message(detected_language: str) -> str:
    """Get response for language switch"""
    validator = get_language_validator()
    return validator.get_language_switch_response(detected_language)

