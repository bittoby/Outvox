// Settings Page - AI Provider Configuration with Animations

import React, { useState, useEffect, useRef } from 'react';
import { 
  Settings2, 
  Zap, 
  Volume2, 
  BrainCircuit, 
  Activity, 
  Loader2,
  ChevronDown,
  Sparkles,
  Waves,
  SlidersHorizontal,
  Bot,
  Check,
  Save,
  RotateCcw,
  Play,
  Square
} from 'lucide-react';
import Card from '../components/Card/Card';
import Button from '../components/Button/Button';
import toast, { Toaster } from 'react-hot-toast';
import { API_CONFIG } from '../services/config';

const API_BASE_URL = API_CONFIG.DB_SERVICE;

type AIProvider = 'openai' | 'elevenlabs';

// OpenAI Realtime Settings
interface OpenAISettings {
  voice: string;
  model: 'gpt-realtime-2025-08-28' | 'gpt-realtime-mini-2025-12-15';
  vadThreshold: number;
  temperature: number;
  maxTokens: number;
}

// ElevenLabs Settings
interface ElevenLabsSettings {
  voiceId: string;
  voiceName: string;
  model: 'eleven_turbo_v2_5' | 'eleven_multilingual_v2' | 'eleven_flash_v2_5';
  stability: number;
  similarityBoost: number;
  language: string;
  agentId: string;
}

// ElevenLabs Voice interface removed - not needed since all config is in ElevenLabs dashboard

const SettingsPage: React.FC = () => {
  const [selectedProvider, setSelectedProvider] = useState<AIProvider>('openai');
  const [saving, setSaving] = useState(false);

  // Voices from API
  const [openaiVoices, setOpenaiVoices] = useState<{id: string; name: string; description: string}[]>([]);
  
  // Dropdown states
  const [openaiVoiceDropdownOpen, setOpenaiVoiceDropdownOpen] = useState(false);
  const openaiDropdownRef = useRef<HTMLDivElement>(null);
  
  // Voice preview state
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  // OpenAI voice preview URLs from CDN (frontend-only, no backend calls)
  // Note: ballad and verse are Realtime-only voices without TTS preview
  const voicePreviewUrls: Record<string, string> = {
    alloy: 'https://cdn.openai.com/API/docs/audio/alloy.wav',
    ash: 'https://cdn.openai.com/API/docs/audio/ash.wav',
    coral: 'https://cdn.openai.com/API/docs/audio/coral.wav',
    echo: 'https://cdn.openai.com/API/docs/audio/echo.wav',
    sage: 'https://cdn.openai.com/API/docs/audio/sage.wav',
    shimmer: 'https://cdn.openai.com/API/docs/audio/shimmer.wav',
    // ballad and verse - Realtime-only, no CDN preview available
  };
  const hasPreview = (voiceId: string) => !!voicePreviewUrls[voiceId];
  const getVoicePreviewUrl = (voiceId: string) => voicePreviewUrls[voiceId] || '';
  
  // Play/stop voice preview
  const toggleVoicePreview = (voiceId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent dropdown item selection
    
    if (playingVoice === voiceId) {
      // Stop playing
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlayingVoice(null);
    } else {
      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause();
      }
      
      // Play new voice using backend API
      const url = getVoicePreviewUrl(voiceId);
      if (url) {
        const audio = new Audio(url);
        audio.onended = () => setPlayingVoice(null);
        audio.onerror = () => {
          toast.error('Failed to load voice preview');
          setPlayingVoice(null);
        };
        audio.play();
        audioRef.current = audio;
        setPlayingVoice(voiceId);
      } else {
        // No preview available for this voice
        toast('Preview not available for this voice', {
          icon: '🎙️',
          duration: 2000,
        });
      }
    }
  };
  
  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // OpenAI Settings State
  const [openaiSettings, setOpenaiSettings] = useState<OpenAISettings>({
    voice: 'alloy',
    model: 'gpt-realtime-2025-08-28',
    vadThreshold: 0.5,
    temperature: 0.8,
    maxTokens: 4096,
  });

  // ElevenLabs Settings State
  const [elevenlabsSettings, setElevenlabsSettings] = useState<ElevenLabsSettings>({
    voiceId: '',
    voiceName: '',
    model: 'eleven_turbo_v2_5',
    stability: 0.5,
    similarityBoost: 0.75,
    language: 'en',
    agentId: '',
  });

  // Default settings
  const defaultOpenaiSettings: OpenAISettings = {
    voice: 'alloy',
    model: 'gpt-realtime-2025-08-28',
    vadThreshold: 0.5,
    temperature: 0.8,
    maxTokens: 4096,
  };

  const defaultElevenlabsSettings: ElevenLabsSettings = {
    voiceId: '',
    voiceName: '',
    model: 'eleven_turbo_v2_5',
    stability: 0.5,
    similarityBoost: 0.75,
    language: 'en',
    agentId: '',
  };

  const resetToDefaults = () => {
    if (selectedProvider === 'openai') {
      setOpenaiSettings(defaultOpenaiSettings);
      toast.success('OpenAI settings reset to defaults');
    } else {
      setElevenlabsSettings(defaultElevenlabsSettings);
      toast.success('ElevenLabs settings reset to defaults');
    }
  };

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (openaiDropdownRef.current && !openaiDropdownRef.current.contains(event.target as Node)) {
        setOpenaiVoiceDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Loading state for initial fetch
  const [loadingSettings, setLoadingSettings] = useState(true);

  // Load saved settings from backend on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/settings/ai-provider`);
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.settings) {
            setSelectedProvider(data.settings.selected_provider || 'openai');
            
            // Map backend snake_case to frontend camelCase
            if (data.settings.openai) {
              setOpenaiSettings({
                voice: data.settings.openai.voice || 'alloy',
                model: data.settings.openai.model || 'gpt-realtime-2025-08-28',
                vadThreshold: data.settings.openai.vad_threshold ?? 0.5,
                temperature: data.settings.openai.temperature ?? 0.8,
                maxTokens: data.settings.openai.max_tokens ?? 4096,
              });
            }
            
            if (data.settings.elevenlabs) {
              setElevenlabsSettings({
                voiceId: data.settings.elevenlabs.voice_id || '',
                voiceName: data.settings.elevenlabs.voice_name || '',
                model: data.settings.elevenlabs.model || 'eleven_turbo_v2_5',
                stability: data.settings.elevenlabs.stability ?? 0.5,
                similarityBoost: data.settings.elevenlabs.similarity_boost ?? 0.75,
                language: data.settings.elevenlabs.language || 'en',
                agentId: data.settings.elevenlabs.agent_id || '',
              });
            }
          }
        }
      } catch (error) {
        console.error('Error loading settings from backend:', error);
        toast.error('Failed to load settings from server');
      } finally {
        setLoadingSettings(false);
      }
    };
    
    loadSettings();
  }, []);

  // Fetch OpenAI voices on mount
  useEffect(() => {
    fetchOpenAIVoices();
  }, []);

  // ElevenLabs voice fetching removed - all config is done in ElevenLabs dashboard

  const fetchOpenAIVoices = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings/openai/voices`);
      if (response.ok) {
        const data = await response.json();
        setOpenaiVoices(data.voices || []);
      }
    } catch (error) {
      console.error('Error fetching OpenAI voices:', error);
    }
  };

  // ElevenLabs voices fetch removed - not needed since all config is in ElevenLabs dashboard

  const handleSave = async () => {
    setSaving(true);
    try {
      // Save to backend API
      const response = await fetch(`${API_BASE_URL}/api/settings/ai-provider`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selected_provider: selectedProvider,
          openai: {
            voice: openaiSettings.voice,
            model: openaiSettings.model,
            vad_threshold: openaiSettings.vadThreshold,
            temperature: openaiSettings.temperature,
            max_tokens: openaiSettings.maxTokens,
          },
          elevenlabs: {
            voice_id: elevenlabsSettings.voiceId,
            voice_name: elevenlabsSettings.voiceName,
            model: elevenlabsSettings.model,
            stability: elevenlabsSettings.stability,
            similarity_boost: elevenlabsSettings.similarityBoost,
            language: elevenlabsSettings.language,
            agent_id: elevenlabsSettings.agentId,
          },
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          toast.success(`Settings saved for ${selectedProvider === 'openai' ? 'OpenAI Realtime' : 'ElevenLabs'}`);
        } else {
          throw new Error(data.message || 'Failed to save');
        }
      } else {
        throw new Error('Server error');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      toast.error('Failed to save settings to server');
    } finally {
      setSaving(false);
    }
  };

  // Get selected OpenAI voice details
  const selectedOpenAIVoice = openaiVoices.find(v => v.id === openaiSettings.voice) || { id: 'alloy', name: 'Alloy', description: 'Neutral and balanced' };

  // Show loading state while fetching settings
  if (loadingSettings) {
    return (
      <div className="max-w-[1600px] mx-auto">
        <Toaster position="top-right" />
        <div className="flex flex-col items-center justify-center py-32">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-4">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
          <p className="text-dark-text-muted font-medium">Loading your settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto space-y-8">
      <Toaster position="top-right" />

      {/* Header with Save Button */}
      <div className="flex justify-between items-start animate-slide-in-left">
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-light to-primary flex items-center justify-center text-white shadow-glow-primary animate-float">
              <Settings2 className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-5xl font-bold bg-gradient-to-r from-dark-text-primary via-primary-light to-primary bg-clip-text text-transparent animate-fade-in">
                Settings
              </h1>
              <p className="text-base text-dark-text-secondary mt-1 animate-slide-in-left stagger-1">
                Configure your AI voice agent system
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={resetToDefaults}
            className="flex items-center gap-2 px-4 py-2.5 text-dark-text-muted hover:text-dark-text-primary bg-dark-elevated rounded-lg border border-dark-border hover:border-primary/50 transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            Reset to Defaults
          </button>
          <Button variant="primary" onClick={handleSave} isLoading={saving} disabled={saving} className="group flex items-center gap-3 px-6 py-3">
            <Save className="w-5 h-5" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* AI Provider Selection - Compact Toggle */}
      <div className="bg-dark-surface border border-dark-border rounded-xl p-1 inline-flex mb-6 animate-fade-in-up stagger-1">
        <button
          onClick={() => setSelectedProvider('openai')}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-base transition-all ${
            selectedProvider === 'openai'
              ? 'bg-primary text-white shadow-md'
              : 'text-dark-text-muted hover:text-dark-text-primary'
          }`}
        >
          <Bot className="w-5 h-5" />
          OpenAI Realtime
        </button>
        <button
          onClick={() => setSelectedProvider('elevenlabs')}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-base transition-all ${
            selectedProvider === 'elevenlabs'
              ? 'bg-primary text-white shadow-md'
              : 'text-dark-text-muted hover:text-dark-text-primary'
          }`}
        >
          <Waves className="w-5 h-5" />
          ElevenLabs
        </button>
      </div>

      {/* Provider Info Banner */}
      <div className={`rounded-xl p-4 mb-6 border animate-fade-in-up stagger-2 ${
        selectedProvider === 'openai' 
          ? 'bg-emerald-500/5 border-emerald-500/20' 
          : 'bg-violet-500/5 border-violet-500/20'
      }`}>
        <div className="flex items-start gap-3">
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${
            selectedProvider === 'openai' 
              ? 'bg-emerald-500/10' 
              : 'bg-violet-500/10'
          }`}>
            {selectedProvider === 'openai' ? (
              <Bot className="w-6 h-6 text-emerald-500" />
            ) : (
              <Waves className="w-6 h-6 text-violet-500" />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold text-dark-text-primary">
                {selectedProvider === 'openai' ? 'OpenAI Realtime API' : 'ElevenLabs Conversational AI'}
              </h3>
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                selectedProvider === 'openai' 
                  ? 'bg-emerald-500/10 text-emerald-400' 
                  : 'bg-violet-500/10 text-violet-400'
              }`}>
                Active
              </span>
            </div>
            <p className="text-sm text-dark-text-muted">
              {selectedProvider === 'openai' 
                ? 'Native AI voice with GPT-4o intelligence • Low latency • ~$0.30/min'
                : 'Ultra-realistic voices with 3000+ options • Voice cloning • ~$0.30/min'
              }
            </p>
          </div>
        </div>
      </div>

      {/* Provider-Specific Settings */}
      {selectedProvider === 'openai' ? (
        <div className="space-y-6 animate-fade-in">
          {/* Voice & Model Section */}
          <Card>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Voice Selection */}
              <div>
                <label className="flex items-center gap-2 text-base font-semibold text-dark-text-primary mb-3">
                  <Volume2 className="w-4 h-4 text-blue-400" />
                  Voice
                </label>
                <div className="relative" ref={openaiDropdownRef}>
                  <button
                    type="button"
                    onClick={() => setOpenaiVoiceDropdownOpen(!openaiVoiceDropdownOpen)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-dark-elevated border border-dark-border rounded-lg text-dark-text-primary hover:border-primary/50 focus:border-primary focus:outline-none transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Volume2 className="w-4 h-4 text-primary" />
                      </div>
                      <div className="text-left">
                        <p className="font-medium text-base">{selectedOpenAIVoice.name}</p>
                        <p className="text-sm text-dark-text-muted">{selectedOpenAIVoice.description}</p>
                      </div>
                    </div>
                    <ChevronDown className={`w-4 h-4 text-dark-text-muted transition-transform ${openaiVoiceDropdownOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {openaiVoiceDropdownOpen && (
                    <div className="absolute z-50 w-full mt-2 bg-dark-surface border border-dark-border rounded-xl shadow-2xl overflow-hidden">
                      <div className="px-3 py-2 border-b border-dark-border bg-dark-elevated/50">
                        <p className="text-xs text-dark-text-muted flex items-center gap-1.5">
                          <Volume2 className="w-3 h-3" />
                          Click play to preview voice
                        </p>
                      </div>
                      <div className="max-h-[280px] overflow-y-auto">
                        {openaiVoices.map((voice) => (
                          <div
                            key={voice.id}
                            onClick={() => {
                              setOpenaiSettings({ ...openaiSettings, voice: voice.id });
                              setOpenaiVoiceDropdownOpen(false);
                            }}
                            className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-all ${
                              openaiSettings.voice === voice.id
                                ? 'bg-primary/10'
                                : 'hover:bg-dark-elevated'
                            }`}
                          >
                            {/* Play/Stop Button - show for voices with TTS preview support */}
                            {hasPreview(voice.id) ? (
                              <button
                                onClick={(e) => toggleVoicePreview(voice.id, e)}
                                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all flex-shrink-0 ${
                                  playingVoice === voice.id
                                    ? 'bg-primary text-white'
                                    : 'bg-dark-elevated hover:bg-primary/20 text-dark-text-muted hover:text-primary'
                                }`}
                                title={playingVoice === voice.id ? 'Stop preview' : 'Play preview'}
                              >
                                {playingVoice === voice.id ? (
                                  <Square className="w-3 h-3" />
                                ) : (
                                  <Play className="w-3 h-3 ml-0.5" />
                                )}
                              </button>
                            ) : (
                              <div 
                                className="w-8 h-8 rounded-full flex items-center justify-center bg-dark-elevated/30 text-dark-text-muted/40 flex-shrink-0"
                                title="Realtime-only voice (no preview)"
                              >
                                <Volume2 className="w-3.5 h-3.5" />
                              </div>
                            )}
                            
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className={`font-medium text-sm ${openaiSettings.voice === voice.id ? 'text-primary' : 'text-dark-text-primary'}`}>
                                  {voice.name}
                                </p>
                                {!hasPreview(voice.id) && (
                                  <span className="text-[10px] px-1.5 py-0.5 bg-violet-500/20 text-violet-400 rounded">REALTIME</span>
                                )}
                              </div>
                              <p className="text-xs text-dark-text-muted truncate">{voice.description}</p>
                            </div>
                            {openaiSettings.voice === voice.id && (
                              <Check className="w-4 h-4 text-primary flex-shrink-0" />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Model Selection */}
              <div>
                <label className="flex items-center gap-2 text-base font-semibold text-dark-text-primary mb-3">
                  <BrainCircuit className="w-4 h-4 text-purple-400" />
                  Model
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setOpenaiSettings({ ...openaiSettings, model: 'gpt-realtime-2025-08-28' })}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      openaiSettings.model === 'gpt-realtime-2025-08-28'
                        ? 'border-primary bg-primary/10'
                        : 'border-dark-border hover:border-primary/50 bg-dark-elevated'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-0.5">
                      <Sparkles className={`w-4 h-4 ${openaiSettings.model === 'gpt-realtime-2025-08-28' ? 'text-primary' : 'text-dark-text-muted'}`} />
                      <p className="font-medium text-base text-dark-text-primary">Standard</p>
                    </div>
                    <p className="text-sm text-dark-text-muted">Best quality</p>
                  </button>
                  <button
                    onClick={() => setOpenaiSettings({ ...openaiSettings, model: 'gpt-realtime-mini-2025-12-15' })}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      openaiSettings.model === 'gpt-realtime-mini-2025-12-15'
                        ? 'border-primary bg-primary/10'
                        : 'border-dark-border hover:border-primary/50 bg-dark-elevated'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-0.5">
                      <Zap className={`w-4 h-4 ${openaiSettings.model === 'gpt-realtime-mini-2025-12-15' ? 'text-primary' : 'text-dark-text-muted'}`} />
                      <p className="font-medium text-base text-dark-text-primary">Mini</p>
                    </div>
                    <p className="text-sm text-dark-text-muted">Faster & cheaper</p>
                  </button>
                </div>
              </div>
            </div>
          </Card>

          {/* Advanced Settings */}
          <Card>
            <h3 className="text-lg font-semibold text-dark-text-primary mb-4 flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-dark-text-muted" />
              Advanced Settings
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* VAD Threshold */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-base text-dark-text-secondary flex items-center gap-2">
                    <Activity className="w-4 h-4 text-orange-400" />
                    VAD Sensitivity
                  </label>
                  <span className="text-base font-mono font-medium text-primary">{openaiSettings.vadThreshold.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.1"
                  value={openaiSettings.vadThreshold}
                  onChange={(e) => setOpenaiSettings({ ...openaiSettings, vadThreshold: parseFloat(e.target.value) })}
                  className="w-full h-1.5 bg-dark-elevated rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-md"
                />
                <div className="flex justify-between text-xs text-dark-text-muted mt-1">
                  <span>More sensitive</span>
                  <span>Less sensitive</span>
                </div>
              </div>

              {/* Temperature */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-base text-dark-text-secondary flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    Creativity
                  </label>
                  <span className="text-base font-mono font-medium text-primary">{openaiSettings.temperature.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.2"
                  step="0.1"
                  value={openaiSettings.temperature}
                  onChange={(e) => setOpenaiSettings({ ...openaiSettings, temperature: parseFloat(e.target.value) })}
                  className="w-full h-1.5 bg-dark-elevated rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-md"
                />
                <div className="flex justify-between text-xs text-dark-text-muted mt-1">
                  <span>Focused</span>
                  <span>Creative</span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in">
          {/* ElevenLabs Info Banner */}
          <div className="p-4 bg-gradient-to-r from-violet-500/10 to-purple-500/10 rounded-xl border border-violet-500/20">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-violet-400" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-dark-text-primary mb-1">ElevenLabs Conversational AI</h3>
                <p className="text-sm text-dark-text-muted">
                  Connect your pre-configured ElevenLabs agent to handle voice calls. 
                  All voice settings, prompts, and AI behavior are managed in the ElevenLabs dashboard.
                </p>
              </div>
            </div>
          </div>

          {/* Agent ID Card */}
          <Card>
            <label className="flex items-center gap-2 text-base font-semibold text-dark-text-primary mb-3">
              <Bot className="w-4 h-4 text-violet-400" />
              Agent ID
              <span className="text-xs text-red-400 font-normal">(Required)</span>
            </label>
            <input
              type="text"
              placeholder="Paste your ElevenLabs Agent ID here..."
              value={elevenlabsSettings.agentId}
              onChange={(e) => setElevenlabsSettings({ ...elevenlabsSettings, agentId: e.target.value })}
              className="w-full px-4 py-3.5 bg-dark-elevated border border-dark-border rounded-lg text-dark-text-primary text-base focus:border-primary focus:outline-none"
            />
            
            {/* Quick Setup Guide */}
            <div className="mt-5 space-y-4">
              <h4 className="text-sm font-semibold text-dark-text-primary flex items-center gap-2">
                <Activity className="w-4 h-4 text-green-400" />
                Quick Setup Guide
              </h4>
              
              <div className="grid gap-3">
                <div className="flex items-start gap-3 p-3 bg-dark-elevated/50 rounded-lg">
                  <span className="w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 text-xs font-bold flex items-center justify-center flex-shrink-0">1</span>
                  <div>
                    <p className="text-sm text-dark-text-primary font-medium">Create your agent</p>
                    <p className="text-xs text-dark-text-muted mt-0.5">
                      Visit <a href="https://elevenlabs.io/app/conversational-ai" target="_blank" rel="noopener noreferrer" className="text-violet-400 hover:underline">ElevenLabs Agents Platform</a> and create a new conversational agent
                    </p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3 p-3 bg-dark-elevated/50 rounded-lg">
                  <span className="w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 text-xs font-bold flex items-center justify-center flex-shrink-0">2</span>
                  <div>
                    <p className="text-sm text-dark-text-primary font-medium">Configure your agent</p>
                    <p className="text-xs text-dark-text-muted mt-0.5">
                      Set up voice, system prompt, first message, and choose your LLM model in the ElevenLabs dashboard
                    </p>
                  </div>
                </div>
                
                <div className="flex items-start gap-3 p-3 bg-dark-elevated/50 rounded-lg">
                  <span className="w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 text-xs font-bold flex items-center justify-center flex-shrink-0">3</span>
                  <div>
                    <p className="text-sm text-dark-text-primary font-medium">Copy the Agent ID</p>
                    <p className="text-xs text-dark-text-muted mt-0.5">
                      Find the Agent ID in your agent's settings and paste it above
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="p-3 bg-amber-500/10 rounded-lg border border-amber-500/20">
                <p className="text-xs text-amber-400">
                  <strong>Important:</strong> Without a valid Agent ID, calls will automatically use OpenAI Realtime instead.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

    </div>
  );
};

export default SettingsPage;
