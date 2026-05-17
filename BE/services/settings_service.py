"""
Settings Service
Provides access to AI provider settings via the DB Service API.
This service is used by voice agents (which may run in Docker containers without DB access).
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# DB Service URL - voice agents connect to db_service via API
DB_SERVICE_URL = os.getenv('DB_SERVICE_URL', 'http://localhost:8000')


@dataclass
class OpenAIRuntimeSettings:
    """Runtime settings for OpenAI Realtime API calls."""
    voice: str = "alloy"
    model: str = "gpt-realtime-2025-08-28"
    vad_threshold: float = 0.5
    temperature: float = 0.8
    max_tokens: int = 4096


@dataclass
class ElevenLabsRuntimeSettings:
    """Runtime settings for ElevenLabs API calls."""
    voice_id: str = ""
    voice_name: str = ""
    model: str = "eleven_turbo_v2_5"
    stability: float = 0.5
    similarity_boost: float = 0.75
    language: str = "en"
    agent_id: str = ""


def get_openai_settings() -> OpenAIRuntimeSettings:
    """
    Fetch OpenAI settings from the DB Service API.
    Falls back to defaults if not found or on error.
    
    Returns:
        OpenAIRuntimeSettings with current configuration
    """
    try:
        response = requests.get(f"{DB_SERVICE_URL}/api/settings/ai-provider", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('settings'):
                openai_data = data['settings'].get('openai', {})
                
                voice = openai_data.get('voice', 'alloy')
                logger.info(f"Loaded OpenAI settings from API - Voice: {voice}, Raw data: {openai_data}")
                
                return OpenAIRuntimeSettings(
                    voice=voice,
                    model=openai_data.get('model', 'gpt-realtime-2025-08-28'),
                    vad_threshold=openai_data.get('vad_threshold', 0.5),
                    temperature=openai_data.get('temperature', 0.8),
                    max_tokens=openai_data.get('max_tokens', 4096)
                )
        
        logger.warning(f"Failed to fetch settings from API (status: {response.status_code}), using defaults")
        return OpenAIRuntimeSettings()
        
    except Exception as e:
        logger.warning(f"Error fetching OpenAI settings from API: {e}. Using defaults.")
        return OpenAIRuntimeSettings()


def get_elevenlabs_settings() -> ElevenLabsRuntimeSettings:
    """
    Fetch ElevenLabs settings from the DB Service API.
    Falls back to defaults if not found or on error.
    
    Returns:
        ElevenLabsRuntimeSettings with current configuration
    """
    try:
        response = requests.get(f"{DB_SERVICE_URL}/api/settings/ai-provider", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('settings'):
                elevenlabs_data = data['settings'].get('elevenlabs', {})
                
                return ElevenLabsRuntimeSettings(
                    voice_id=elevenlabs_data.get('voice_id', ''),
                    voice_name=elevenlabs_data.get('voice_name', ''),
                    model=elevenlabs_data.get('model', 'eleven_turbo_v2_5'),
                    stability=elevenlabs_data.get('stability', 0.5),
                    similarity_boost=elevenlabs_data.get('similarity_boost', 0.75),
                    language=elevenlabs_data.get('language', 'en'),
                    agent_id=elevenlabs_data.get('agent_id', '')
                )
        
        logger.warning(f"Failed to fetch ElevenLabs settings from API (status: {response.status_code}), using defaults")
        return ElevenLabsRuntimeSettings()
        
    except Exception as e:
        logger.warning(f"Error fetching ElevenLabs settings from API: {e}. Using defaults.")
        return ElevenLabsRuntimeSettings()


def get_active_provider() -> str:
    """
    Get the currently active AI provider.
    
    Returns:
        'openai' or 'elevenlabs'
    """
    try:
        response = requests.get(f"{DB_SERVICE_URL}/api/settings/ai-provider", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('settings'):
                return data['settings'].get('selected_provider', 'openai')
        
        return 'openai'
        
    except Exception as e:
        logger.warning(f"Error fetching active provider from API: {e}. Defaulting to OpenAI.")
        return 'openai'
