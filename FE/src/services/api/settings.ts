/**
 * Settings API Service
 *
 * Handles AI provider settings and voice fetching.
 *
 * Uses `axios` for HTTP — the global X-API-Key header installed by
 * services/authBootstrap.ts only attaches to axios requests, so any use of
 * the native fetch() API here would silently drop authentication and hit
 * 401 against an API-key-protected backend.
 */

import axios from 'axios';

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
 * Get AI provider settings from backend.
 */
export const getAIProviderSettings = async (): Promise<AIProviderSettingsResponse> => {
  const response = await axios.get<AIProviderSettingsResponse>(
    `${API_BASE_URL}/api/settings/ai-provider`
  );
  return response.data;
};

/**
 * Save AI provider settings to backend.
 */
export const saveAIProviderSettings = async (
  settings: SaveSettingsRequest
): Promise<AIProviderSettingsResponse> => {
  const response = await axios.post<AIProviderSettingsResponse>(
    `${API_BASE_URL}/api/settings/ai-provider`,
    settings
  );
  return response.data;
};

/**
 * Get the current AI provider setting (quick check).
 */
export const getActiveProvider = async (): Promise<AIProvider> => {
  try {
    const response = await axios.get<{ provider: AIProvider }>(
      `${API_BASE_URL}/api/settings/ai-provider/active`
    );
    return response.data.provider;
  } catch (error) {
    console.error('Failed to get active provider:', error);
    return 'openai';
  }
};

/**
 * Get the current AI provider setting (sync version for backward compatibility).
 * Falls back to localStorage if API not available.
 */
export const getAIProvider = (): AIProvider => {
  const saved = localStorage.getItem('ai_provider_cache');
  if (saved === 'openai' || saved === 'elevenlabs') {
    return saved;
  }
  return 'openai';
};

/**
 * Save the AI provider setting (sync version for backward compatibility).
 * Updates localStorage cache.
 */
export const saveAIProvider = (provider: AIProvider): void => {
  localStorage.setItem('ai_provider_cache', provider);
};

/**
 * Check if ElevenLabs is enabled.
 */
export const isElevenLabsEnabled = (): boolean => {
  return getAIProvider() === 'elevenlabs';
};

/**
 * Check if OpenAI is enabled.
 */
export const isOpenAIEnabled = (): boolean => {
  return getAIProvider() === 'openai';
};

/**
 * Fetch ElevenLabs voices from backend.
 */
export const fetchElevenLabsVoices = async () => {
  const response = await axios.get(`${API_BASE_URL}/api/settings/elevenlabs/voices`);
  return response.data;
};

/**
 * Fetch OpenAI voices from backend.
 */
export const fetchOpenAIVoices = async () => {
  const response = await axios.get(`${API_BASE_URL}/api/settings/openai/voices`);
  return response.data;
};
