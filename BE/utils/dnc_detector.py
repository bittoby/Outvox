"""
Do Not Call (DNC) Detection Module
Advanced detection of DNC requests using pattern matching and sentiment analysis.
"""

import re
from typing import Tuple, List
from config import config


class DNCDetector:
    """Detects Do Not Call requests in customer responses"""
    
    def __init__(self):
        self.dnc_phrases = config.dnc.DNC_PHRASES
        
        # Strong rejection patterns (immediate DNC)
        self.strong_rejection_patterns = [
            r'\b(never|don\'t ever|stop|cease|remove|unsubscribe)\b.*\b(call|contact|reach|text|message|email)',
            r'\b(call|contact|reach|text|message|email)\b.*\b(stop|cease)\b',
            r'\bstop\b.*\b(harassing|bothering|calling)\b',
            r'\b(take me|remove me)\b.*\b(off|from).*\b(list|calls)',
            r'\bleave me alone\b',
            r'\bdo not call\b',
            r'\bdon\'t call\b',
            r'\bnot interested\b.*\b(at all|whatsoever|never)',
        ]
        
        # Soft rejection patterns (potential DNC)
        self.soft_rejection_patterns = [
            r'\bnot interested\b',
            r'\bno thanks\b',
            r'\bnot right now\b',
            r'\bmaybe later\b',
            r'\bbusy right now\b',
        ]
    
    def is_dnc_request(self, text: str) -> Tuple[bool, str, float]:
        """
        Check if text contains a DNC request
        
        Args:
            text: Customer's text to analyze
            
        Returns:
            Tuple[bool, str, float]: (is_dnc, reason, confidence)
                - is_dnc: True if DNC detected
                - reason: Description of why it's DNC
                - confidence: 0.0-1.0 confidence score
        """
        if not text or not text.strip():
            return False, "", 0.0
        
        text_lower = text.lower()
        
        # Check exact phrase matches
        for phrase in self.dnc_phrases:
            if phrase.lower() in text_lower:
                return True, f"Exact match: '{phrase}'", 1.0
        
        # Check strong rejection patterns
        for pattern in self.strong_rejection_patterns:
            if re.search(pattern, text_lower):
                return True, f"Strong rejection pattern", 0.9
        
        # Check soft rejection patterns (lower confidence)
        for pattern in self.soft_rejection_patterns:
            if re.search(pattern, text_lower):
                # Count occurrences - repeated = higher confidence
                count = len(re.findall(pattern, text_lower))
                if count >= 2:
                    return True, f"Repeated soft rejection ({count}x)", 0.7
                else:
                    return False, f"Soft rejection (not strong enough)", 0.4
        
        return False, "No DNC indicators", 0.0
    
    def analyze_sentiment(self, text: str) -> float:
        """
        Simple sentiment analysis (-1.0 to 1.0)
        
        Args:
            text: Text to analyze
            
        Returns:
            float: Sentiment score (-1.0 = very negative, 1.0 = very positive)
        """
        if not text:
            return 0.0
        
        text_lower = text.lower()
        
        # Positive indicators
        positive_words = [
            'yes', 'sure', 'okay', 'great', 'sounds good', 'interested',
            'tell me more', 'how much', 'when', 'where', 'perfect',
            'thanks', 'appreciate', 'helpful'
        ]
        
        # Negative indicators (single words)
        negative_words = [
            'no', 'never', 'stop', 'hate', 'angry', 'annoying',
            'frustrated', 'upset', 'bad', 'terrible', 'awful',
            'horrible', 'dislike', 'mad', 'annoyed', 'irritating'
        ]
        
        # Negative indicator phrases
        negative_phrases = [
            'not interested',
            'leave me alone',
            'go away',
            'bad time',
            'stop calling',
            'do not call',
            'don\'t call'
        ]
        
        # Count positive and negative words (use word boundary matching to avoid false positives like "now" matching "no")
        words_in_text = set(re.findall(r'\b\w+\b', text_lower))
        positive_count = sum(1 for word in positive_words if word in text_lower and (len(word.split()) > 1 or word in words_in_text))
        negative_count = sum(1 for word in negative_words if word in words_in_text)  # Single words must match exactly
        
        # Count negative phrases (each phrase counts as one)
        negative_phrase_count = sum(1 for phrase in negative_phrases if phrase in text_lower)
        negative_count += negative_phrase_count
        
        # Calculate sentiment
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
        
        # Normalize by text length
        positive_score = positive_count / max(total_words, 1)
        negative_score = negative_count / max(total_words, 1)
        
        # Return normalized score
        sentiment = (positive_score - negative_score) * 2
        return max(-1.0, min(1.0, sentiment))
    
    def should_end_call(self, text: str) -> Tuple[bool, str]:
        """
        Determine if call should end based on DNC or sentiment
        
        Args:
            text: Customer's text to analyze
            
        Returns:
            Tuple[bool, str]: (should_end, reason)
        """
        # Check for DNC request
        is_dnc, reason, confidence = self.is_dnc_request(text)
        if is_dnc and confidence >= 0.7:
            return True, f"DNC request: {reason}"
        
        # Check sentiment
        sentiment = self.analyze_sentiment(text)
        if sentiment <= config.dnc.SENTIMENT_THRESHOLD:
            return True, f"Negative sentiment: {sentiment:.2f}"
        
        return False, "Continue call"
    
    def get_dnc_response(self) -> str:
        """Get polite response for DNC request"""
        return (
            "I understand, I'll remove your number from our list immediately. "
            "You won't receive any more calls from us. Have a great day!"
        )
    
    def log_dnc_patterns(self, text: str) -> List[str]:
        """
        Log which patterns triggered (for debugging/improvement)
        
        Args:
            text: Text that triggered DNC
            
        Returns:
            List[str]: List of matched patterns
        """
        matches = []
        text_lower = text.lower()
        
        # Check phrases
        for phrase in self.dnc_phrases:
            if phrase.lower() in text_lower:
                matches.append(f"Phrase: {phrase}")
        
        # Check patterns
        for pattern in self.strong_rejection_patterns:
            if re.search(pattern, text_lower):
                matches.append(f"Strong pattern: {pattern}")
        
        for pattern in self.soft_rejection_patterns:
            if re.search(pattern, text_lower):
                matches.append(f"Soft pattern: {pattern}")
        
        return matches


# Global instance
_dnc_detector = None


def get_dnc_detector() -> DNCDetector:
    """Get singleton instance of DNCDetector"""
    global _dnc_detector
    if _dnc_detector is None:
        _dnc_detector = DNCDetector()
    return _dnc_detector


# Convenience functions
def check_dnc_request(text: str) -> Tuple[bool, str, float]:
    """Check if text contains DNC request"""
    detector = get_dnc_detector()
    return detector.is_dnc_request(text)


def analyze_customer_sentiment(text: str) -> float:
    """Analyze sentiment of customer text"""
    detector = get_dnc_detector()
    return detector.analyze_sentiment(text)


def should_end_call_now(text: str) -> Tuple[bool, str]:
    """Determine if call should end"""
    detector = get_dnc_detector()
    return detector.should_end_call(text)

