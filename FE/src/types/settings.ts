// Settings and configuration types

export type AIProvider = 'openai' | 'elevenlabs';

export interface AIProviderSettings {
  provider: AIProvider;
}

export interface SystemSettings {
  aiProvider: AIProviderSettings;
}

