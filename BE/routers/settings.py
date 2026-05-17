"""
Settings Router
Handles AI provider settings and voice fetching.
"""

import os
import json
import logging
import aiohttp
from datetime import datetime
from contextlib import contextmanager
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

from models.settings import (
    OpenAISettings,
    ElevenLabsSettings,
    AIProviderSettings,
    SaveSettingsRequest,
)

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    import pyodbc
    SQL_SERVER = os.getenv('SQLServer')
    SQL_USER = os.getenv('SQLUser')
    SQL_PASSWORD = os.getenv('SQLPassword')
    SQL_DATABASE = os.getenv('SQLDatabase')
    
    if SQL_SERVER and "localdb" in SQL_SERVER.lower():
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"Trusted_Connection=yes;"
        )
    else:
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
    
    conn = pyodbc.connect(connection_string)
    try:
        yield conn
    finally:
        conn.close()


router = APIRouter(prefix="/api/settings", tags=["settings"])

# ElevenLabs API configuration
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


def get_elevenlabs_api_key() -> str:
    """Get ElevenLabs API key from environment (loaded dynamically)."""
    return os.getenv('ELEVENLABS_API_KEY', '')

# Settings key for the database
SETTINGS_KEY = "ai_provider_settings"


def ensure_settings_table():
    """Ensure the SystemSettings table exists."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SystemSettings')
                BEGIN
                    CREATE TABLE SystemSettings (
                        setting_key NVARCHAR(100) PRIMARY KEY,
                        setting_value NVARCHAR(MAX) NOT NULL,
                        updated_at DATETIME2 DEFAULT GETDATE(),
                        created_at DATETIME2 DEFAULT GETDATE()
                    )
                END
            """)
            conn.commit()
            cursor.close()
    except Exception as e:
        logger.error(f"Error ensuring settings table: {e}")


# Ensure table exists on module load
ensure_settings_table()


@router.get("/ai-provider")
async def get_ai_provider_settings():
    """
    Get the current AI provider settings.
    
    Returns:
        AI provider settings including selected provider and provider-specific configs
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setting_value, updated_at 
                FROM SystemSettings 
                WHERE setting_key = ?
            """, (SETTINGS_KEY,))
            row = cursor.fetchone()
            cursor.close()
        
        if row:
            settings_data = json.loads(row[0])
            updated_at = row[1]
            
            # Parse into Pydantic models for validation
            settings = AIProviderSettings(
                selected_provider=settings_data.get('selected_provider', 'openai'),
                openai=OpenAISettings(**settings_data.get('openai', {})),
                elevenlabs=ElevenLabsSettings(**settings_data.get('elevenlabs', {}))
            )
            
            return {
                "success": True,
                "settings": settings.model_dump(),
                "updated_at": updated_at.isoformat() if updated_at else None
            }
        else:
            # Return default settings
            default_settings = AIProviderSettings()
            return {
                "success": True,
                "settings": default_settings.model_dump(),
                "updated_at": None
            }
            
    except Exception as e:
        logger.error(f"Error getting AI provider settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@router.post("/ai-provider")
async def save_ai_provider_settings(request: SaveSettingsRequest):
    """
    Save AI provider settings.
    
    Args:
        request: Settings to save including selected provider and provider-specific configs
    
    Returns:
        Success status and saved settings
    """
    try:
        settings_json = json.dumps({
            "selected_provider": request.selected_provider,
            "openai": request.openai.model_dump(),
            "elevenlabs": request.elevenlabs.model_dump()
        })
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                MERGE SystemSettings AS target
                USING (SELECT ? AS setting_key, ? AS setting_value) AS source
                ON target.setting_key = source.setting_key
                WHEN MATCHED THEN
                    UPDATE SET setting_value = source.setting_value, updated_at = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (setting_key, setting_value, created_at, updated_at)
                    VALUES (source.setting_key, source.setting_value, GETDATE(), GETDATE());
            """, (SETTINGS_KEY, settings_json))
            conn.commit()
            cursor.close()
        
        logger.info(f"Saved AI provider settings: {request.selected_provider}")
        
        return {
            "success": True,
            "message": f"Settings saved for {request.selected_provider}",
            "settings": {
                "selected_provider": request.selected_provider,
                "openai": request.openai.model_dump(),
                "elevenlabs": request.elevenlabs.model_dump()
            },
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error saving AI provider settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")


@router.get("/ai-provider/active")
async def get_active_provider():
    """
    Get just the currently active AI provider name.
    
    Returns:
        The currently selected provider ('openai' or 'elevenlabs')
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setting_value 
                FROM SystemSettings 
                WHERE setting_key = ?
            """, (SETTINGS_KEY,))
            row = cursor.fetchone()
            cursor.close()
        
        if row:
            settings_data = json.loads(row[0])
            return {"provider": settings_data.get('selected_provider', 'openai')}
        return {"provider": "openai"}
            
    except Exception as e:
        logger.error(f"Error getting active provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active provider: {str(e)}")


@router.get("/elevenlabs/voices")
async def get_elevenlabs_voices(source: str = "all"):
    """
    Fetch voices from ElevenLabs API.
    
    Args:
        source: "personal" (your cloned voices), "library" (shared 3000+ voices), or "all" (both)
    
    Returns:
        List of voices with voice_id, name, category, labels, and preview_url
    """
    api_key = get_elevenlabs_api_key()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ElevenLabs API key not configured. Please set ELEVENLABS_API_KEY in .env"
        )
    
    all_voices = []
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            # 1. Fetch user's personal/cloned voices (if requested)
            if source in ["personal", "all"]:
                async with session.get(
                    f"{ELEVENLABS_API_URL}/voices",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        voices = data.get("voices", [])
                        
                        for voice in voices:
                            all_voices.append({
                                "voice_id": voice.get("voice_id"),
                                "name": voice.get("name"),
                                "category": voice.get("category", "personal"),
                                "labels": voice.get("labels", {}),
                                "preview_url": voice.get("preview_url", "")
                            })
                        
                        logger.info(f"Fetched {len(voices)} personal ElevenLabs voices")
                    
                    elif response.status == 401:
                        raise HTTPException(
                            status_code=401,
                            detail="Invalid ElevenLabs API key"
                        )
            
            # 2. Fetch shared voices from the voice library (if requested)
            if source in ["library", "all"]:
                # Fetch multiple pages to get more voices (up to 500)
                page_size = 100
                for page in range(5):  # Get up to 500 voices
                    async with session.get(
                        f"{ELEVENLABS_API_URL}/shared-voices",
                        headers=headers,
                        params={"page_size": page_size, "page": page}
                    ) as lib_response:
                        if lib_response.status == 200:
                            lib_data = await lib_response.json()
                            shared_voices = lib_data.get("voices", [])
                            
                            if not shared_voices:
                                break  # No more voices
                            
                            for voice in shared_voices:
                                # Avoid duplicates
                                if not any(v["voice_id"] == voice.get("voice_id") for v in all_voices):
                                    all_voices.append({
                                        "voice_id": voice.get("voice_id"),
                                        "name": voice.get("name"),
                                        "category": voice.get("category", "library"),
                                        "labels": voice.get("labels", {}),
                                        "preview_url": voice.get("preview_url", "")
                                    })
                            
                            # Check if there are more pages
                            if not lib_data.get("has_more", False):
                                break
                        else:
                            logger.warning(f"Failed to fetch shared voices page {page}: {lib_response.status}")
                            break
                
                logger.info(f"Total ElevenLabs voices fetched: {len(all_voices)}")
            
            return {"voices": all_voices, "count": len(all_voices)}
                    
    except aiohttp.ClientError as e:
        logger.error(f"Failed to connect to ElevenLabs API: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to connect to ElevenLabs API"
        )


@router.get("/openai/voices")
async def get_openai_voices():
    """
    Return available OpenAI Realtime API voices.
    
    Note: OpenAI doesn't have a voices API endpoint, so we return a static list.
    Official Realtime API voices: alloy, ash, ballad, coral, echo, sage, shimmer, verse
    Reference: https://mastra.ai/reference/voice/openai-realtime
    """
    voices = [
        # Official OpenAI Realtime API voices (8 voices)
        {"id": "alloy", "name": "Alloy", "description": "Neutral and balanced"},
        {"id": "ash", "name": "Ash", "description": "Clear and precise"},
        {"id": "ballad", "name": "Ballad", "description": "Melodic and smooth"},
        {"id": "coral", "name": "Coral", "description": "Warm and friendly"},
        {"id": "echo", "name": "Echo", "description": "Resonant and deep"},
        {"id": "sage", "name": "Sage", "description": "Calm and thoughtful"},
        {"id": "shimmer", "name": "Shimmer", "description": "Bright and energetic"},
        {"id": "verse", "name": "Verse", "description": "Versatile and expressive"},
    ]
    
    return {"voices": voices, "count": len(voices)}


