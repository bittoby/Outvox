"""
Call Result Detection Module
Intelligent determination of call results based on conversation analysis.
"""

import re
from typing import Tuple, List
from config import config


class CallResultDetector:
    """Detects call results based on conversation analysis"""
    
    def __init__(self):
        # Interest indicators - customer shows genuine interest
        self.interest_indicators = [
            'directions', 'where are you', 'visit', 'come in', 'address', 'hours',
            'open', 'location', 'how do i get', 'what time', 'today', 'tomorrow',
            'bring', 'appraisal', 'evaluate', 'worth', 'value', 'loan', 'cash',
            'gold', 'jewelry', 'watch', 'electronics', 'pawn', 'borrow',
            'yes', 'sure', 'okay', 'alright', 'sounds good', 'interested',
            'tell me more', 'how much', 'what do you need', 'requirements'
        ]
        
        # Callback request indicators - customer wants to be called back
        self.callback_indicators = [
            'call back', 'call me back', 'call me later', 'call tomorrow',
            'call next week', 'call when', 'busy now', 'not right now',
            'later', 'tomorrow', 'next week', 'when i have time',
            'remind me', 'follow up', 'check back'
        ]
        
        # Not interested indicators - polite rejection
        self.not_interested_indicators = [
            'not interested', 'no thanks', 'not right now', 'maybe later',
            'not today', 'not this week', 'not sure', 'don\'t think so',
            'probably not', 'unlikely', 'not for me', 'not my thing',
            'not looking', 'don\'t need', 'no need', 'all set'
        ]
        
        # Strong rejection patterns (these are definitely DNC)
        self.strong_rejection_patterns = [
            r'\b(never|don\'t ever|stop|cease|remove|unsubscribe)\b.*\b(call|contact|reach)',
            r'\b(take me|remove me)\b.*\b(off|from).*\b(list|calls)',
            r'\bleave me alone\b',
            r'\bdo not call\b',
            r'\bstop calling\b',
            r'\bremove my number\b',
            r'\bdon\'t call me\b',
            r'\bnever call me\b',
            r'\bnot interested.*at all.*never\b',
        ]
    
    def analyze_conversation(self, customer_transcript: str, agent_transcript: str) -> Tuple[str, str, float]:
        """
        Analyze conversation to determine call result
        
        Args:
            customer_transcript: What the customer said
            agent_transcript: What the agent said
            
        Returns:
            Tuple[str, str, float]: (result_type, reason, confidence)
                - result_type: 'interested', 'not_interested', 'callback', 'dnc'
                - reason: Human-readable explanation
                - confidence: 0.0-1.0 confidence score
        """
        if not customer_transcript or not customer_transcript.strip():
            return "not_interested", "No customer input", 0.5
        
        customer_lower = customer_transcript.lower()
        
        # Check for DNC first (highest priority)
        dnc_result = self._check_dnc(customer_lower)
        if dnc_result[0]:
            return "dnc", dnc_result[1], dnc_result[2]
        
        # Check for callback requests
        callback_result = self._check_callback(customer_lower)
        if callback_result[0]:
            return "callback", callback_result[1], callback_result[2]
        
        # Check for not interested
        not_interested_result = self._check_not_interested(customer_lower)
        if not_interested_result[0]:
            return "not_interested", not_interested_result[1], not_interested_result[2]
        
        # Check for interest
        interest_result = self._check_interest(customer_lower)
        if interest_result[0]:
            return "interested", interest_result[1], interest_result[2]
        
        # Default to not_interested if no clear indicators
        return "not_interested", "No clear indicators", 0.3
    
    def _check_dnc(self, text: str) -> Tuple[bool, str, float]:
        """Check for Do Not Call indicators - only very explicit requests"""
        # Check exact DNC phrases from config (must be exact matches)
        for phrase in config.dnc.DNC_PHRASES:
            if phrase.lower() in text.lower():
                return True, f"DNC phrase: '{phrase}'", 1.0
        
        # Check strong rejection patterns (more specific)
        for pattern in self.strong_rejection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True, "Strong rejection pattern", 0.9
        
        # Additional check: multiple negative indicators together
        negative_count = 0
        negative_indicators = ['not interested', 'no thanks', 'not right now', 'maybe later']
        for indicator in negative_indicators:
            if indicator in text.lower():
                negative_count += 1
        
        # Only mark as DNC if multiple negative indicators AND explicit request
        if negative_count >= 2 and any(phrase in text.lower() for phrase in ['call', 'contact', 'reach']):
            return True, "Multiple negative indicators with contact request", 0.8
        
        return False, "", 0.0
    
    def _check_callback(self, text: str) -> Tuple[bool, str, float]:
        """Check for callback request indicators"""
        matches = []
        for indicator in self.callback_indicators:
            if indicator in text:
                matches.append(indicator)
        
        if matches:
            confidence = min(0.9, 0.5 + (len(matches) * 0.1))
            return True, f"Callback indicators: {', '.join(matches)}", confidence
        
        return False, "", 0.0
    
    def _check_not_interested(self, text: str) -> Tuple[bool, str, float]:
        """Check for not interested indicators"""
        matches = []
        for indicator in self.not_interested_indicators:
            if indicator in text:
                matches.append(indicator)
        
        if matches:
            confidence = min(0.8, 0.4 + (len(matches) * 0.1))
            return True, f"Not interested indicators: {', '.join(matches)}", confidence
        
        return False, "", 0.0
    
    def _check_interest(self, text: str) -> Tuple[bool, str, float]:
        """Check for interest indicators"""
        matches = []
        for indicator in self.interest_indicators:
            if indicator in text:
                matches.append(indicator)
        
        if matches:
            confidence = min(0.9, 0.5 + (len(matches) * 0.1))
            return True, f"Interest indicators: {', '.join(matches)}", confidence
        
        return False, "", 0.0
    
    def get_result_explanation(self, result_type: str) -> str:
        """Get human-readable explanation for result type"""
        explanations = {
            "interested": "Customer showed genuine interest in visiting the store",
            "not_interested": "Customer politely declined the service",
            "callback": "Customer requested to be called back at a different time",
            "dnc": "Customer requested to be removed from calling list",
            "completed": "Call completed without clear outcome indicators"
        }
        return explanations.get(result_type, "Unknown result type")
    
    def log_analysis(self, customer_transcript: str, result_type: str, reason: str, confidence: float) -> None:
        """Log the analysis for debugging and improvement"""
        print(f"[CALL_RESULT] Analysis:")
        print(f"  Customer: {customer_transcript[:100]}...")
        print(f"  Result: {result_type}")
        print(f"  Reason: {reason}")
        print(f"  Confidence: {confidence:.2f}")


# Global instance
_call_result_detector = None

def get_call_result_detector() -> CallResultDetector:
    """Get the global call result detector instance"""
    global _call_result_detector
    if _call_result_detector is None:
        _call_result_detector = CallResultDetector()
    return _call_result_detector

def determine_call_result(customer_transcript: str, agent_transcript: str = "") -> Tuple[str, str, float]:
    """
    Determine call result based on conversation analysis
    
    Args:
        customer_transcript: What the customer said
        agent_transcript: What the agent said (optional)
        
    Returns:
        Tuple[str, str, float]: (result_type, reason, confidence)
    """
    detector = get_call_result_detector()
    result_type, reason, confidence = detector.analyze_conversation(customer_transcript, agent_transcript)
    
    # Log the analysis
    detector.log_analysis(customer_transcript, result_type, reason, confidence)
    
    return result_type, reason, confidence
