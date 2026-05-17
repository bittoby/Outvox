"""
Settings Models
Pydantic models for AI provider settings.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class OpenAISettings(BaseModel):
    """OpenAI Realtime API settings"""
    voice: str = Field(default="alloy", description="Voice ID for OpenAI TTS")
    model: Literal['gpt-realtime-2025-08-28', 'gpt-realtime-mini-2025-12-15'] = Field(
        default='gpt-realtime-2025-08-28',
        description="OpenAI realtime model"
    )
    vad_threshold: float = Field(default=0.5, ge=0.1, le=1.0, description="Voice Activity Detection threshold")
    temperature: float = Field(default=0.8, ge=0.1, le=1.2, description="Response creativity")
    max_tokens: int = Field(default=4096, ge=256, le=16384, description="Maximum response tokens")


class ElevenLabsSettings(BaseModel):
    """ElevenLabs Conversational AI settings"""
    voice_id: str = Field(default="", description="ElevenLabs voice ID")
    voice_name: str = Field(default="", description="Voice display name")
    model: Literal['eleven_turbo_v2_5', 'eleven_multilingual_v2', 'eleven_flash_v2_5'] = Field(
        default='eleven_turbo_v2_5',
        description="ElevenLabs speech model"
    )
    stability: float = Field(default=0.5, ge=0.0, le=1.0, description="Voice stability")
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0, description="Voice similarity boost")
    language: str = Field(default="en", description="Language code")
    agent_id: str = Field(default="", description="ElevenLabs Agent ID for Conversational AI")


class AIProviderSettings(BaseModel):
    """Complete AI provider settings"""
    selected_provider: Literal['openai', 'elevenlabs'] = Field(
        default='openai',
        description="Currently selected AI provider"
    )
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    elevenlabs: ElevenLabsSettings = Field(default_factory=ElevenLabsSettings)


class AIProviderSettingsResponse(BaseModel):
    """Response model for AI provider settings"""
    success: bool
    settings: AIProviderSettings
    updated_at: Optional[datetime] = None


class SaveSettingsRequest(BaseModel):
    """Request model for saving settings"""
    selected_provider: Literal['openai', 'elevenlabs']
    openai: OpenAISettings
    elevenlabs: ElevenLabsSettings
