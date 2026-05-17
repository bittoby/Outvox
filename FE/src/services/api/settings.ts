/**
 * Settings API Service
 * Handles AI provider settings and configuration via backend API
 */

import type { AIProvider } from '../../types/settings';
import { API_CONFIG } from '../config';

const API_BASE_URL = API_CONFIG.DB_SERVICE;

// Types for API responses
export interface OpenAISettings {
  voice: string;
  model: 'gpt-realtime-2025-08-28' | 'gpt-realtime-mini-2025-12-15';
  vad_threshold: number;
  temperature: number;
  max_tokens: number;
}

export interface ElevenLabsSettings {
  voice_id: string;
  voice_name: string;
  model: 'eleven_turbo_v2_5' | 'eleven_multilingual_v2' | 'eleven_flash_v2_5';
  stability: number;
  similarity_boost: number;
  language: string;
  agent_id: string;
}

export interface AIProviderSettingsResponse {
  success: boolean;
  settings: {
    selected_provider: AIProvider;
    openai: OpenAISettings;
    elevenlabs: ElevenLabsSettings;
  };
  updated_at: string | null;
}

export interface SaveSettingsRequest {
  selected_provider: AIProvider;
  openai: OpenAISettings;
  elevenlabs: ElevenLabsSettings;
}

/**
 * Get AI provider settings from backend
 */
export const getAIProviderSettings = async (): Promise<AIProviderSettingsResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/settings/ai-provider`);
  if (!response.ok) {
    throw new Error('Failed to fetch AI provider settings');
  }
  return response.json();
};

/**
 * Save AI provider settings to backend
 */
export const saveAIProviderSettings = async (settings: SaveSettingsRequest): Promise<AIProviderSettingsResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/settings/ai-provider`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(settings),
  });
  if (!response.ok) {
    throw new Error('Failed to save AI provider settings');
  }
  return response.json();
};

/**
 * Get the current AI provider setting (quick check)
 */
export const getActiveProvider = async (): Promise<AIProvider> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/settings/ai-provider/active`);
    if (response.ok) {
      const data = await response.json();
      return data.provider;
    }
  } catch (error) {
    console.error('Failed to get active provider:', error);
  }
  return 'openai'; // Default to OpenAI
};

/**
 * Get the current AI provider setting (sync version for backward compatibility)
 * Falls back to localStorage if API not available
 */
export const getAIProvider = (): AIProvider => {
  const saved = localStorage.getItem('ai_provider_cache');
  if (saved === 'openai' || saved === 'elevenlabs') {
    return saved;
  }
  return 'openai'; // Default to OpenAI
};

/**
 * Save the AI provider setting (sync version for backward compatibility)
 * Updates localStorage cache
 */
export const saveAIProvider = (provider: AIProvider): void => {
  localStorage.setItem('ai_provider_cache', provider);
};

/**
 * Check if ElevenLabs is enabled
 */
export const isElevenLabsEnabled = (): boolean => {
  return getAIProvider() === 'elevenlabs';
};

/**
 * Check if OpenAI is enabled
 */
export const isOpenAIEnabled = (): boolean => {
  return getAIProvider() === 'openai';
};

/**
 * Fetch ElevenLabs voices from backend
 */
export const fetchElevenLabsVoices = async () => {
  const response = await fetch(`${API_BASE_URL}/api/settings/elevenlabs/voices`);
  if (!response.ok) {
    throw new Error('Failed to fetch ElevenLabs voices');
  }
  return response.json();
};

/**
 * Fetch OpenAI voices from backend
 */
export const fetchOpenAIVoices = async () => {
  const response = await fetch(`${API_BASE_URL}/api/settings/openai/voices`);
  if (!response.ok) {
    throw new Error('Failed to fetch OpenAI voices');
  }
  return response.json();
};
