"""
Prompt Loader - Dynamic prompt management system for the AI voice agent.

Prompt files on disk reference the company and the agent via the placeholders
``{company_name}``, ``{company_short_name}``, ``{agent_name}``,
``{company_offering}``, and ``{company_tagline}``. These are substituted from
``config.brand`` at load time. The ``{customer_name}`` and ``{agent_name}``
placeholders in greeting templates remain unresolved at load time so they can
be filled in per-call.
"""

import os
import json
import random
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

# Get the base directory (Outbound/)
BASE_DIR = Path(__file__).parent.parent
PROMPTS_DIR = BASE_DIR / 'prompts'


def _brand_vars() -> Dict[str, str]:
    """Return the brand substitution dict, loaded lazily to avoid import cycles."""
    try:
        from config import config
        return {
            'company_name': config.brand.COMPANY_NAME,
            'company_short_name': config.brand.COMPANY_SHORT_NAME,
            'agent_name': config.brand.AGENT_NAME,
            'company_tagline': config.brand.COMPANY_TAGLINE,
            'company_offering': config.brand.COMPANY_OFFERING,
        }
    except Exception:
        # Fallback during early imports / setup scripts.
        return {
            'company_name': os.getenv('COMPANY_NAME', 'Acme Pawn'),
            'company_short_name': os.getenv('COMPANY_SHORT_NAME', 'Acme'),
            'agent_name': os.getenv('AGENT_NAME', 'Alex'),
            'company_tagline': os.getenv(
                'COMPANY_TAGLINE',
                'Trusted local pawn loans and appraisals.'
            ),
            'company_offering': os.getenv(
                'COMPANY_OFFERING',
                'pawn loans and quick cash for gold, jewelry, watches, and electronics'
            ),
        }


def apply_brand_substitution(text: str) -> str:
    """
    Replace ``{company_name}`` / ``{agent_name}`` / etc. with config values.

    Uses ``str.replace`` rather than ``str.format`` so that unrelated
    placeholders (e.g., ``{customer_name}``) survive untouched.
    """
    if not text:
        return text
    out = text
    for key, value in _brand_vars().items():
        out = out.replace('{' + key + '}', value)
    return out


def _apply_brand_recursive(obj: Any) -> Any:
    """Apply brand substitution to every string in a nested dict/list."""
    if isinstance(obj, str):
        return apply_brand_substitution(obj)
    if isinstance(obj, list):
        return [_apply_brand_recursive(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _apply_brand_recursive(v) for k, v in obj.items()}
    return obj


class PromptLoader:
    """Manages loading and formatting of AI agent prompts."""

    def __init__(self):
        self.base_prompt = self._load_base_prompt()
        self.training_examples = self._load_training_examples()
        self.greeting_variations = self._load_greeting_variations()

    def _load_base_prompt(self) -> str:
        """Load the base system prompt with brand substitution applied."""
        prompt_file = PROMPTS_DIR / 'base_prompt.txt'
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return apply_brand_substitution(f.read())
        except FileNotFoundError:
            print(f"Warning: Base prompt file not found at {prompt_file}")
            return self._get_fallback_prompt()

    def _load_training_examples(self) -> list:
        """Load training examples for objection handling."""
        examples_file = PROMPTS_DIR / 'training_examples.json'
        try:
            with open(examples_file, 'r', encoding='utf-8') as f:
                return _apply_brand_recursive(json.load(f))
        except FileNotFoundError:
            print(f"Warning: Training examples not found at {examples_file}")
            return []

    def _load_greeting_variations(self) -> dict:
        """Load greeting variations."""
        greetings_file = PROMPTS_DIR / 'greeting_variations.json'
        try:
            with open(greetings_file, 'r', encoding='utf-8') as f:
                return _apply_brand_recursive(json.load(f))
        except FileNotFoundError:
            print(f"Warning: Greeting variations not found at {greetings_file}")
            brand = _brand_vars()
            return {
                'default': [
                    f"Hi {{customer_name}}, this is {{agent_name}} from {brand['company_name']}—"
                ]
            }

    def _get_fallback_prompt(self) -> str:
        """Fallback prompt if file loading fails."""
        brand = _brand_vars()
        return (
            f"You are a professional loan specialist for {brand['company_name']}. "
            f"Your mission: bring new customers into stores for {brand['company_offering']}. "
            "Be confident, friendly, and direct. Keep responses under 30 words. "
            "Always end by inviting the customer to visit today or tomorrow."
        )
    
    def get_system_prompt(self,
                         customer_name: str = None,
                         closest_location: str = None,
                         agent_name: str = None) -> str:
        """
        Get the complete system prompt with dynamic variables filled in.
        
        Args:
            customer_name: Customer's name for personalization
            closest_location: Suggested closest store location
            agent_name: Name of the agent making the call
            
        Returns:
            str: Formatted system prompt
        """
        brand = _brand_vars()
        if not agent_name:
            agent_name = brand['agent_name']

        prompt = self.base_prompt

        # Add dynamic context
        dynamic_context = "\n\n=== CURRENT CALL CONTEXT ===\n"

        if customer_name:
            dynamic_context += f"Customer name: {customer_name}\n"
            dynamic_context += f"Address customer as: {customer_name}\n"
        else:
            dynamic_context += "Customer name: Unknown (don't use a name until they provide it)\n"

        if closest_location:
            dynamic_context += f"Suggested closest location: {closest_location}\n"
            dynamic_context += "Mention this location first, but offer all locations.\n"

        dynamic_context += f"Your agent name: {agent_name}\n"
        dynamic_context += f"Current date: {datetime.now().strftime('%A, %B %d, %Y')}\n"
        dynamic_context += f"Current time: {datetime.now().strftime('%I:%M %p')}\n"

        # Add call start instruction
        dynamic_context += (
            "\n=== START THE CALL NOW ===\n"
            "Customer just picked up. YOU speak first.\n"
            f"Opening: \"Hey [name], it's {agent_name} from {brand['company_name']}. "
            "Quick thing - you can ask us to stop calling anytime, and this might be recorded. "
            "Anyway, got a sec?\"\n"
            "Then immediately steer into the offering. Keep responses 1-2 sentences max.\n"
        )

        prompt += dynamic_context

        return prompt
    
    def get_greeting(self, customer_name: str = None, agent_name: str = None) -> str:
        """
        Get a random greeting variation based on time of day.
        
        Args:
            customer_name: Customer's name for personalization
            agent_name: Agent's name
            
        Returns:
            str: Formatted greeting
        """
        hour = datetime.now().hour
        
        # Determine time of day
        if 5 <= hour < 12:
            time_period = 'morning'
        elif 12 <= hour < 17:
            time_period = 'afternoon'
        elif 17 <= hour < 22:
            time_period = 'evening'
        else:
            time_period = 'default'
        
        # Get greetings for this time period
        greetings = self.greeting_variations.get(time_period,
                                                 self.greeting_variations.get('default', []))

        # Select random greeting
        greeting_template = random.choice(greetings)

        if not agent_name:
            agent_name = _brand_vars()['agent_name']

        # Format with variables
        greeting = greeting_template.format(
            customer_name=customer_name or "there",
            agent_name=agent_name
        )

        return greeting
    
    def get_training_example(self, objection_type: str) -> Optional[Dict]:
        """
        Get a training example for a specific objection type.
        
        Args:
            objection_type: Type of objection (e.g., "busy", "think_about_it")
            
        Returns:
            dict: Training example or None if not found
        """
        # Map objection types to keywords in training examples
        objection_keywords = {
            'busy': 'busy',
            'think_about_it': 'think about',
            'not_sure': 'not sure',
            'location': 'where',
            'rates': 'rates',
            'what_buy': 'what do you buy',
            'picture': 'picture',
            'already_have': 'already have'
        }
        
        keyword = objection_keywords.get(objection_type, '')
        if not keyword:
            return None
        
        # Find matching training example
        for example in self.training_examples:
            if keyword.lower() in example['instruction'].lower():
                return example
        
        return None
    
    def get_all_training_examples_as_context(self) -> str:
        """
        Get all training examples formatted as context for the AI.
        
        Returns:
            str: Formatted training examples
        """
        if not self.training_examples:
            return ""
        
        context = "\n\n=== EXAMPLE RESPONSES (Use as reference, adapt naturally) ===\n"
        for example in self.training_examples:
            context += f"\nSituation: {example['instruction']}\n"
            context += f"Example response: {example['response']}\n"
        
        return context
    
    def format_prompt_with_variables(self, text: str, **kwargs) -> str:
        """
        Format a prompt template with variables.
        
        Args:
            text: Template text with {variable} placeholders
            **kwargs: Variable values
            
        Returns:
            str: Formatted text
        """
        try:
            return text.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing variable in prompt: {e}")
            return text

# Global instance for easy import
_prompt_loader = None

def get_prompt_loader() -> PromptLoader:
    """Get singleton instance of PromptLoader."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader

# Convenience functions
def get_system_prompt(customer_name: str = None,
                     closest_location: str = None,
                     agent_name: str = None) -> str:
    """Convenience function to get system prompt."""
    loader = get_prompt_loader()
    return loader.get_system_prompt(customer_name, closest_location, agent_name)


def get_greeting(customer_name: str = None, agent_name: str = None) -> str:
    """Convenience function to get greeting."""
    loader = get_prompt_loader()
    return loader.get_greeting(customer_name, agent_name)

# For testing
if __name__ == "__main__":
    # Test prompt loader
    loader = PromptLoader()
    
    print("=== BASE PROMPT ===")
    print(loader.base_prompt[:200] + "...")
    
    print("\n=== SYSTEM PROMPT WITH CONTEXT ===")
    prompt = loader.get_system_prompt(
        customer_name="John Smith",
        closest_location="Downtown",
        agent_name="Agent OUT1"
    )
    print(prompt[:500] + "...")
    
    print("\n=== GREETING VARIATIONS ===")
    for _ in range(3):
        print(loader.get_greeting("John", "Agent OUT1"))
    
    print("\n=== TRAINING EXAMPLE ===")
    example = loader.get_training_example('busy')
    if example:
        print(f"Objection: {example['instruction']}")
        print(f"Response: {example['response']}")
