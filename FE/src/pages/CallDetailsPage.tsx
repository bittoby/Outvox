// Call Details Page - Detailed view of a single call

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, Phone, Clock, User, CheckCircle, 
  MapPin, Calendar, FileText, Play, Pause 
} from 'lucide-react';
import Card from '../components/Card/Card';
import Badge from '../components/Badge/Badge';
import toast, { Toaster } from 'react-hot-toast';
import { getCallDetails } from '../services/api';
import { API_CONFIG } from '../services/config';
import type { CallDetails } from '../types/call';

const CallDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [callDetails, setCallDetails] = useState<CallDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Track playback state if needed for future UI; not currently used
  // (intentionally omitted to avoid linter warning)
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (id) {
      fetchCallDetails(parseInt(id));
    }
  }, [id]);

  const fetchCallDetails = async (resultId: number) => {
    try {
      setLoading(true);
      const data = await getCallDetails(resultId);
      setCallDetails(data);
    } catch (error) {
      console.error('Error fetching call details:', error);
      toast.error('Failed to load call details');
      navigate('/history');
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    if (!seconds || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return {
        date: new Intl.DateTimeFormat('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        }).format(date),
        time: new Intl.DateTimeFormat('en-US', {
          hour: '2-digit',
          minute: '2-digit'
        }).format(date),
        full: date.toLocaleString('en-US')
      };
    } catch {
      return { date: 'N/A', time: 'N/A', full: 'N/A' };
    }
  };

  const getResultBadge = (result: string) => {
    const config: Record<string, { variant: 'success' | 'error' | 'info' | 'warning' | 'neutral'; label: string }> = {
      interested: { variant: 'success', label: 'Interested' },
      not_interested: { variant: 'error', label: 'Not Interested' },
      callback: { variant: 'info', label: 'Callback' },
      dnc: { variant: 'warning', label: 'DNC' },
      completed: { variant: 'neutral', label: 'Completed' },
    };
    const c = config[result] || { variant: 'neutral', label: result };
    return <Badge variant={c.variant} size="sm">{c.label}</Badge>;
  };

  const parseTranscript = (combinedTranscript: string, callDuration: number) => {
    const entries: Array<{ speaker: string; text: string; timestamp: string }> = [];
    
    // Use combined_transcript which maintains chronological order
    // If not available, fall back to empty array
    if (!combinedTranscript || !combinedTranscript.trim()) {
      return entries;
    }
    
    // Parse the combined transcript line by line
    // Format: "Customer: text\nAgent: text\nCustomer: text..."
    const lines = combinedTranscript.split('\n').filter(line => line.trim());
    
    let currentSpeaker: string | null = null;
    let currentMessage: string[] = [];
    
    lines.forEach((line) => {
      const customerMatch = line.match(/^Customer:\s*(.+)$/i);
      const agentMatch = line.match(/^Agent:\s*(.+)$/i);
      
      if (customerMatch) {
        // Save previous entry if exists
        if (currentSpeaker && currentMessage.length > 0) {
          entries.push({
            speaker: currentSpeaker,
            text: currentMessage.join(' ').trim(),
            timestamp: '' // Will calculate below
          });
          currentMessage = [];
        }
        currentSpeaker = 'Customer';
        currentMessage.push(customerMatch[1].trim());
      } else if (agentMatch) {
        // Save previous entry if exists
        if (currentSpeaker && currentMessage.length > 0) {
          entries.push({
            speaker: currentSpeaker,
            text: currentMessage.join(' ').trim(),
            timestamp: '' // Will calculate below
          });
          currentMessage = [];
        }
        currentSpeaker = 'Agent';
        currentMessage.push(agentMatch[1].trim());
      } else if (line.trim() && currentSpeaker) {
        // Continuation of current speaker's message
        currentMessage.push(line.trim());
      }
    });
    
    // Don't forget the last entry
    if (currentSpeaker && currentMessage.length > 0) {
      entries.push({
        speaker: currentSpeaker,
        text: currentMessage.join(' ').trim(),
        timestamp: ''
      });
    }
    
    // Calculate approximate timestamps based on position in conversation
    const totalEntries = entries.length;
    entries.forEach((entry, index) => {
      const approximateTime = Math.floor((index / Math.max(totalEntries, 1)) * callDuration);
      const mins = Math.floor(approximateTime / 60);
      const secs = approximateTime % 60;
      entry.timestamp = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    });
    
    return entries;
  };

  const generateCallSummary = (details: CallDetails): string => {
    const resultType = details.result_type;
    const hasLocation = details.lead_city || details.lead_address;
    
    if (resultType === 'interested') {
      return `Customer expressed interest in pawn loan services. ${hasLocation ? `Located in ${details.lead_city || 'area'}. ` : ''}Agent provided information about loan options and store locations. ${details.customer_transcript.includes('direction') || details.customer_transcript.includes('location') ? 'Customer requested location information. ' : ''}Call concluded successfully with customer interest confirmed.`;
    } else if (resultType === 'callback') {
      return `Customer requested a callback at a more convenient time. Agent provided initial information about services. Customer contact details verified.`;
    } else if (resultType === 'dnc') {
      return `Customer requested to be removed from calling list (Do Not Call). Customer preferences respected. Number marked as DNC.`;
    } else if (resultType === 'not_interested') {
      return `Customer declined interest in services at this time. Agent provided brief information about available services. Call ended politely.`;
    }
    
    return `Call completed with result: ${resultType}. ${hasLocation ? `Customer location: ${details.lead_city || details.lead_address || 'Unknown'}. ` : ''}${details.customer_transcript ? `Key points discussed during conversation.` : ''}`;
  };

  const extractActionsTaken = (details: CallDetails): Array<{ title: string; description: string; timestamp: string }> => {
    const actions: Array<{ title: string; description: string; timestamp: string }> = [];
    
    if (details.customer_transcript.includes('direction') || details.customer_transcript.includes('location')) {
      actions.push({
        title: 'Directions Provided',
        description: 'Sent store location and directions via SMS',
        timestamp: formatTime(Math.floor(details.call_duration * 0.8))
      });
    }
    
    if (details.result_type === 'interested') {
      actions.push({
        title: 'Service Information',
        description: 'Explained pawn loan services and terms',
        timestamp: formatTime(Math.floor(details.call_duration * 0.3))
      });
    }
    
    if (details.result_type === 'dnc') {
      actions.push({
        title: 'DNC Marked',
        description: 'Marked customer as Do Not Call',
        timestamp: formatTime(details.call_duration)
      });
    }
    
    if (details.customer_transcript.includes('appraisal') || details.customer_transcript.includes('photo')) {
      actions.push({
        title: 'Photo Request',
        description: 'Customer requested photo appraisal information',
        timestamp: formatTime(Math.floor(details.call_duration * 0.6))
      });
    }
    
    return actions.length > 0 ? actions : [{
      title: 'Call Completed',
      description: 'Conversation ended successfully',
      timestamp: formatTime(details.call_duration)
    }];
  };

  const extractInformationGathered = (details: CallDetails) => {
    const info: Array<{ icon: React.ReactNode; label: string; value: string }> = [];
    
    if (details.lead_name) {
      info.push({
        icon: <User className="w-4 h-4" />,
        label: 'Customer Name',
        value: details.lead_name
      });
    }
    
    if (details.phone_number) {
      info.push({
        icon: <Phone className="w-4 h-4" />,
        label: 'Phone Number',
        value: details.phone_number
      });
    }
    
    const fullAddress = [
      details.lead_address,
      details.lead_city,
      details.lead_state,
      details.lead_zip
    ].filter(Boolean).join(', ');
    
    if (fullAddress) {
      info.push({
        icon: <MapPin className="w-4 h-4" />,
        label: 'Address',
        value: fullAddress
      });
    }
    
    if (details.lead_county) {
      info.push({
        icon: <MapPin className="w-4 h-4" />,
        label: 'County',
        value: details.lead_county
      });
    }
    
    info.push({
      icon: <Clock className="w-4 h-4" />,
      label: 'Call Duration',
      value: formatDuration(details.call_duration)
    });
    
    info.push({
      icon: <FileText className="w-4 h-4" />,
      label: 'Call Result',
      value: details.result_type.replace('_', ' ').toUpperCase()
    });
    
    return info;
  };

  if (loading) {
    return (
      <div className="max-w-[1600px] mx-auto space-y-6">
        <div className="flex items-center gap-4 animate-slide-in-left">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-warning to-warning-dark flex items-center justify-center text-white shadow-glow-warning animate-float">
            <FileText className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-warning-light to-warning bg-clip-text text-transparent">
              Loading...
            </h1>
          </div>
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 bg-dark-elevated border border-dark-border rounded-xl animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!callDetails) {
    return null;
  }

  const dateInfo = formatDate(callDetails.timestamp);
  // Use combined_transcript if available (chronological), otherwise fall back to parsing separate transcripts
  const transcriptEntries = callDetails.combined_transcript
    ? parseTranscript(callDetails.combined_transcript, callDetails.call_duration)
    : parseTranscript(
        `${callDetails.customer_transcript}\n${callDetails.agent_transcript}`,
        callDetails.call_duration
      );
  const summary = generateCallSummary(callDetails);
  const actions = extractActionsTaken(callDetails);
  const information = extractInformationGathered(callDetails);

  return (
    <div className="max-w-[1600px] mx-auto space-y-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex items-center gap-4 animate-slide-in-left">
        <button
          onClick={() => navigate('/history')}
          className="w-10 h-10 rounded-lg bg-dark-elevated border-2 border-dark-border hover:border-primary/40 flex items-center justify-center text-dark-text-primary hover:text-primary transition-all"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-warning to-warning-dark flex items-center justify-center text-white shadow-glow-warning animate-float">
          <FileText className="w-7 h-7" />
        </div>
        <div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-warning-light to-warning bg-clip-text text-transparent">
            Call Details
          </h1>
          <p className="text-sm text-dark-text-secondary mt-1">
            {callDetails.lead_name || 'Unknown Customer'} • {dateInfo.full}
          </p>
        </div>
      </div>

      {/* Call Information Card */}
      <Card>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-2xl font-bold text-dark-text-primary">
                {callDetails.lead_name || 'Unknown Customer'}
              </h2>
              {getResultBadge(callDetails.result_type)}
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-primary-light" />
                <div>
                  <p className="text-xs text-dark-text-muted">Type</p>
                  <p className="text-sm font-semibold text-dark-text-primary">Outbound</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-info-light" />
                <div>
                  <p className="text-xs text-dark-text-muted">Agent</p>
                  <p className="text-sm font-semibold text-dark-text-primary">{callDetails.agent_id}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-warning-light" />
                <div>
                  <p className="text-xs text-dark-text-muted">Duration</p>
                  <p className="text-sm font-semibold text-dark-text-primary font-mono">
                    {formatDuration(callDetails.call_duration)}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-success-light" />
                <div>
                  <p className="text-xs text-dark-text-muted">Date</p>
                  <p className="text-sm font-semibold text-dark-text-primary">{dateInfo.date}</p>
                  <p className="text-xs text-dark-text-muted">{dateInfo.time}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Audio Player Card */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-dark-text-primary">Call Recording</h3>
          </div>
          {/* Hidden audio element; custom controls below */}
          <audio
            ref={audioRef}
            preload="metadata"
            src={`${API_CONFIG.DB_SERVICE}/api/calls/call-recording/${encodeURIComponent(callDetails.call_sid)}`}
            style={{ display: 'none' }}
            onLoadedMetadata={() => {
              const raw = audioRef.current?.duration;
              const fallback = callDetails.call_duration || 0;
              const dur = (!raw || !isFinite(raw) || isNaN(raw)) ? fallback : Math.floor(raw);
              setDuration(dur);
            }}
            onDurationChange={() => {
              const raw = audioRef.current?.duration;
              const fallback = callDetails.call_duration || 0;
              const dur = (!raw || !isFinite(raw) || isNaN(raw)) ? fallback : Math.floor(raw);
              setDuration(dur);
            }}
            onTimeUpdate={() => {
              const ctRaw = audioRef.current?.currentTime || 0;
              setCurrentTime(Math.floor(isFinite(ctRaw) ? ctRaw : 0));
            }}
            onEnded={() => {
              // ensure progress reaches end
              if (duration) setCurrentTime(duration);
            }}
            onError={() => {
              if (!duration) setDuration(callDetails.call_duration || 0);
            }}
          />

          {/* Custom controls + progress bar */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                if (!audioRef.current) return;
                if ((audioRef.current as any).paused) {
                  const p = audioRef.current.play();
                  if (p && typeof p.then === 'function') p.catch(() => undefined);
                } else {
                  audioRef.current.pause();
                }
              }}
              className="w-12 h-12 rounded-lg bg-primary hover:bg-primary-light border-2 border-primary-dark flex items-center justify-center text-white transition-all hover:scale-105"
              title={(audioRef.current && (audioRef.current as any).paused) ? 'Play' : 'Pause'}
            >
              {(audioRef.current && (audioRef.current as any).paused) ? <Play className="w-6 h-6" /> : <Pause className="w-6 h-6" />}
            </button>

            <div className="flex-1 space-y-1">
            <div
              className="relative h-3 bg-dark-surface rounded-full overflow-hidden border border-dark-border cursor-pointer"
              onClick={(e) => {
                if (!audioRef.current || duration === 0) return;
                const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const next = Math.max(0, Math.min(1, clickX / rect.width)) * duration;
                audioRef.current.currentTime = next;
                setCurrentTime(next);
              }}
            >
              <div
                className="h-full bg-gradient-to-r from-primary to-primary-light rounded-full transition-all duration-150"
                style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-dark-text-muted">
              <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration || callDetails.call_duration || 0)}</span>
            </div>
            </div>
          </div>

          <p className="text-xs text-dark-text-muted">If the recording does not play, it may be unavailable for this call.</p>
        </div>
      </Card>

      {/* Call Summary */}
      <Card>
        <h3 className="text-lg font-bold text-dark-text-primary mb-4">Call Summary</h3>
        <p className="text-sm text-dark-text-secondary leading-relaxed">
          {summary}
        </p>
      </Card>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Transcript */}
        <Card>
          <h3 className="text-lg font-bold text-dark-text-primary mb-4">Live Transcript</h3>
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {transcriptEntries.length > 0 ? (
              transcriptEntries.map((entry, index) => {
                const isAgent = entry.speaker.toLowerCase() === 'agent';
                return (
                  <div
                    key={index}
                    className={`flex gap-3 ${isAgent ? 'flex-row-reverse' : ''}`}
                  >
                    <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                      isAgent 
                        ? 'bg-primary/20 text-primary-light border-2 border-primary/30' 
                        : 'bg-info/20 text-info-light border-2 border-info/30'
                    }`}>
                      {isAgent ? (
                        <User className="w-5 h-5" />
                      ) : (
                        <Phone className="w-5 h-5" />
                      )}
                    </div>
                    <div className={`flex-1 flex flex-col ${isAgent ? 'items-end' : 'items-start'} max-w-[75%]`}>
                      <div className={`p-3 rounded-2xl ${
                        isAgent
                          ? 'bg-primary/15 border border-primary/30 rounded-br-sm'
                          : 'bg-dark-elevated border border-dark-border rounded-bl-sm'
                      }`}>
                        <p className="text-xs font-semibold text-dark-text-muted mb-1.5">
                          {entry.speaker} {entry.timestamp && (
                            <span className="text-dark-text-muted/70 font-mono">• {entry.timestamp}</span>
                          )}
                        </p>
                        <p className="text-sm text-dark-text-primary leading-relaxed whitespace-pre-wrap break-words">{entry.text}</p>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-dark-text-muted">No transcript available</p>
            )}
          </div>
        </Card>

        {/* Actions Taken & Information Gathered */}
        <div className="space-y-6">
          {/* Actions Taken */}
          <Card>
            <h3 className="text-lg font-bold text-dark-text-primary mb-4">Actions Taken</h3>
            <div className="space-y-3">
              {actions.map((action, index) => (
                <div key={index} className="flex gap-3">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-success/20 flex items-center justify-center mt-0.5">
                    <CheckCircle className="w-4 h-4 text-success-light" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-semibold text-dark-text-primary">{action.title}</p>
                      <p className="text-xs text-dark-text-muted font-mono">{action.timestamp}</p>
                    </div>
                    <p className="text-xs text-dark-text-secondary">{action.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Information Gathered */}
          <Card>
            <h3 className="text-lg font-bold text-dark-text-primary mb-4">Information Gathered</h3>
            <div className="grid grid-cols-1 gap-3">
              {information.map((info, index) => (
                <div key={index} className="flex items-center gap-3 p-3 bg-dark-elevated border border-dark-border rounded-lg">
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary-light">
                    {info.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-dark-text-muted mb-0.5">{info.label}</p>
                    <p className="text-sm font-medium text-dark-text-primary truncate">{info.value}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default CallDetailsPage;

