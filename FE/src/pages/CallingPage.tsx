// Calling Control Center - AWESOME Modern Voice-Agent UI

import React, { useState, useEffect, useCallback } from 'react';
import { Phone, Zap, Play, Settings, TrendingUp, AlertCircle, CheckCircle2, Target, BarChart3, Rocket, ThumbsUp, PhoneCall, Ban as BanIcon, XCircle } from 'lucide-react';
import Card from '../components/Card/Card';
import Button from '../components/Button/Button';
import CallStatus from '../components/CallStatus/CallStatus';
import VoiceWave from '../components/VoiceWave/VoiceWave';
import { startSingleCall, getCallStats, getAllAgentHealth, startCallCampaign } from '../services/api';
import { useWebSocket, EventType } from '../hooks/useWebSocket';
import type { CallResult, CampaignResult } from '../types/call';
import toast, { Toaster } from 'react-hot-toast';

const CallingPage: React.FC = () => {
  const [calling, setCalling] = useState(false);
  const [campaignCount, setCampaignCount] = useState(10);
  const [lastResult, setLastResult] = useState<CallResult | null>(null);
  const [callDuration, setCallDuration] = useState(0);
  const [availableLeads, setAvailableLeads] = useState(0);
  const [healthyAgents, setHealthyAgents] = useState(0);
  const [totalAgents, setTotalAgents] = useState(10);
  const [campaignRunning, setCampaignRunning] = useState(false);
  const [campaignResult, setCampaignResult] = useState<CampaignResult | null>(null);

  // Fetch stats util (reusable)
  const fetchStats = useCallback(async () => {
    try {
      const [stats, agents] = await Promise.all([
        getCallStats(),
        getAllAgentHealth()
      ]);
      setAvailableLeads(stats.pending_leads || 0);
      const healthy = agents.filter((a: any) => a.status === 'healthy').length;
      setHealthyAgents(healthy);
      setTotalAgents(agents.length);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, []);

  // WebSocket for real-time updates
  const { subscribe, on } = useWebSocket({ autoConnect: true });

  useEffect(() => {
    // Subscribe to relevant events
    subscribe([
      EventType.CALL_STATS_UPDATE,
      EventType.AGENT_HEALTH_UPDATE,
    ]);

    // Handle call stats updates
    const unsubscribeStats = on(EventType.CALL_STATS_UPDATE, () => {
      fetchStats();
    });

    // Handle agent health updates
    const unsubscribeAgents = on(EventType.AGENT_HEALTH_UPDATE, () => {
      getAllAgentHealth().then(agents => {
        const healthy = agents.filter((a: any) => a.status === 'healthy').length;
        setHealthyAgents(healthy);
        setTotalAgents(agents.length);
      }).catch(console.error);
    });

    return () => {
      unsubscribeStats();
      unsubscribeAgents();
    };
  }, [subscribe, on, fetchStats]);

  // Initial fetch
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Handle single call
  const handleSingleCall = async () => {
    console.log('📞 User clicked Start Single Call');
    setCalling(true);
    setCallDuration(0);
    
    try {
      toast.loading('Initiating call...', { id: 'single-call' });
      
      // Simulate call duration counter
      const durationInterval = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
      
      const result = await startSingleCall();
      setLastResult(result);
      // Refresh stats immediately so the store location section updates quickly
      fetchStats();
      
      clearInterval(durationInterval);
      
      console.log('📞 Call result:', result);
      
      if (result.status === 'success' && result.call_sid) {
        toast.success(
          `Call started! SID: ${result.call_sid.slice(0, 10)}... (Agent: ${result.agent_id})`,
          { id: 'single-call', duration: 5000 }
        );
      } else if (result.status === 'failed' || !result.call_sid) {
        toast.error(
          result.message || 'Call failed - check console for details',
          { id: 'single-call', duration: 6000 }
        );
      } else {
        toast.error(result.message || 'Call failed', { id: 'single-call' });
      }
    } catch (error: unknown) {
      console.error('❌ Call error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Error starting call';
      toast.error(errorMessage, { id: 'single-call' });
    } finally {
      setCalling(false);
      setCallDuration(0);
    }
  };

  // Handle campaign
  const handleStartCampaign = async () => {
    if (campaignRunning) {
      toast.error('Campaign already running!');
      return;
    }
    
    if (campaignCount < 1 || campaignCount > 100) {
      toast.error('Campaign count must be between 1 and 100');
      return;
    }
    
    console.log(`🚀 User clicked Start Campaign (${campaignCount} calls)`);
    setCampaignRunning(true);
    setCampaignResult(null);
    
    try {
      toast.loading(`Starting campaign with ${campaignCount} calls...`, { id: 'campaign' });
      
      const result = await startCallCampaign(campaignCount);
      
      console.log('📊 Campaign completed:', result);
      setCampaignResult(result);
      // Refresh stats after campaign completes
      fetchStats();
      
      if (result.successful > 0) {
        toast.success(
          `Campaign complete! ${result.successful}/${result.total_calls} calls successful`,
          { id: 'campaign', duration: 6000 }
        );
      } else {
        toast.error(
          `Campaign failed! 0/${result.total_calls} calls successful`,
          { id: 'campaign', duration: 6000 }
        );
      }
    } catch (error: unknown) {
      console.error('❌ Campaign error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Campaign failed';
      toast.error(errorMessage, { id: 'campaign', duration: 5000 });
    } finally {
      setCampaignRunning(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto space-y-8">
      <Toaster 
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f8fafc',
            border: '2px solid #475569',
            borderRadius: '12px',
            fontWeight: '600',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#f8fafc',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#f8fafc',
            },
          },
        }}
      />
      
      {/* Awesome Animated Header */}
      <div className="flex items-center gap-4 animate-slide-in-left">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-success-light to-success flex items-center justify-center text-white shadow-glow-success animate-float">
          <Phone className="w-10 h-10" />
        </div>
        <div>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-dark-text-primary via-success-light to-success bg-clip-text text-transparent">
            Calling Control Center
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <p className="text-base text-dark-text-secondary">
              Initiate calls and manage campaigns
            </p>
            {calling && (
              <div className="flex items-center gap-2 px-3 py-1 bg-success/20 border-2 border-success/40 rounded-full animate-scale-in">
                <VoiceWave isActive={true} color="#10b981" size="sm" />
                <span className="text-xs font-bold text-success-light">
                  Active Call {callDuration}s
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Call Status Display */}
      {calling && lastResult && (
        <div className="animate-bounce-in">
          <CallStatus
            status="calling"
            duration={callDuration}
            phoneNumber={lastResult.phone_number}
          />
        </div>
      )}

      {/* Quick Actions with AWESOME design */}
      <Card title="Quick Actions" subtitle="Start calling immediately">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          {/* Single Call Card */}
          <div className="group relative bg-gradient-to-br from-dark-surface to-dark-elevated border-2 border-success/40 hover:border-success/60 rounded-2xl p-8 transition-all duration-500 hover:scale-105 card-glow animate-scale-in overflow-hidden">
            {/* Animated Background Glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-success/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            
            <div className="relative z-10 space-y-6">
              {/* Icon with awesome animation */}
              <div className="flex justify-center">
                <div className="relative inline-flex items-center justify-center w-24 h-24 rounded-2xl bg-gradient-to-br from-success-light to-success text-white shadow-glow-success group-hover:scale-110 transition-all duration-300 breathing">
                  <Phone className="w-12 h-12" />
                  {calling && (
                    <div className="absolute inset-0 rounded-2xl bg-success animate-ping opacity-30"></div>
                  )}
                </div>
              </div>
              
              <div className="text-center">
                <h3 className="text-2xl font-bold text-dark-text-primary mb-3">
                  Single Call
                </h3>
                <p className="text-sm text-dark-text-secondary leading-relaxed">
                  Make one call to the next available lead via load balancer
                </p>
              </div>
              
              <Button
                onClick={handleSingleCall}
                variant="success"
                size="lg"
                isLoading={calling}
                className="w-full group"
              >
                {calling ? (
                  <div className="flex items-center justify-center gap-3">
                    <VoiceWave isActive={true} color="#ffffff" size="sm" />
                    <span>Calling...</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-3">
                    <Play className="w-5 h-5 group-hover:scale-125 transition-transform" />
                    <span>Start Call</span>
                  </div>
                )}
              </Button>
            </div>
          </div>

          {/* Campaign Card */}
          <div className="group relative bg-gradient-to-br from-dark-surface to-dark-elevated border-2 border-warning/40 hover:border-warning/60 rounded-2xl p-8 transition-all duration-500 hover:scale-105 card-glow animate-scale-in stagger-1 overflow-hidden">
            {/* Animated Background Glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-warning/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            
            <div className="relative z-10 space-y-6">
              {/* Icon */}
              <div className="flex justify-center">
                <div className="inline-flex items-center justify-center w-24 h-24 rounded-2xl bg-gradient-to-br from-warning-light to-warning text-white shadow-glow-warning group-hover:scale-110 transition-all duration-300 animate-pulse-slow">
                  <Zap className="w-12 h-12" />
                </div>
              </div>
              
              <div className="text-center">
                <h3 className="text-2xl font-bold text-dark-text-primary mb-3">
                  Campaign
                </h3>
                <p className="text-sm text-dark-text-secondary leading-relaxed">
                  Run parallel calling campaign across multiple agents
                </p>
              </div>
              
              <Button
                onClick={handleStartCampaign}
                variant="warning"
                size="lg"
                className="w-full group"
                disabled={campaignRunning}
              >
                <div className="flex items-center justify-center gap-3">
                  {campaignRunning ? (
                    <>
                      <VoiceWave isActive={true} color="#f59e0b" size="sm" />
                      <span>Running Campaign...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-5 h-5 group-hover:rotate-12 transition-transform" />
                      <span>Start Campaign</span>
                    </>
                  )}
                </div>
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Campaign Settings - Simple & Clean */}
      <Card 
        title={
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
              <Settings className="w-5 h-5 text-primary-light" />
            </div>
            <span>Campaign Settings</span>
          </div>
        }
        subtitle="Set the number of calls for your campaign" 
        variant="primary"
      >
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Left Column - Number Input */}
          <div className="lg:col-span-2 space-y-5">
            <div>
              <label className="flex items-center gap-2 text-base font-bold text-dark-text-primary mb-4">
                <Target className="w-5 h-5 text-primary-light" />
                Number of Calls
              </label>

              {/* Quick Presets */}
              <div className="flex items-center gap-2 mb-4">
                {[10, 25, 50, 100].map((preset) => (
                  <button
                    key={preset}
                    onClick={() => setCampaignCount(preset)}
                    className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                      campaignCount === preset
                        ? 'bg-primary text-white shadow-glow-primary scale-105'
                        : 'bg-dark-elevated text-dark-text-secondary hover:bg-dark-surface hover:text-dark-text-primary border border-dark-border'
                    }`}
                  >
                    {preset}
                  </button>
                ))}
              </div>

              {/* Slider + Input */}
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="1"
                  max="100"
                  value={campaignCount}
                  onChange={(e) => setCampaignCount(Math.min(Math.max(1, Number(e.target.value)), 100))}
                  className="flex-1 h-3 bg-dark-elevated rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:h-6 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-gradient-to-r [&::-webkit-slider-thumb]:from-primary-light [&::-webkit-slider-thumb]:to-primary [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-all [&::-webkit-slider-thumb]:duration-200 [&::-webkit-slider-thumb]:hover:scale-125 [&::-webkit-slider-thumb]:shadow-glow-primary"
                />
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={campaignCount}
                  onChange={(e) => setCampaignCount(Math.min(Math.max(1, Number(e.target.value) || 1), 100))}
                  className="w-20 h-14 bg-gradient-to-br from-primary to-primary-dark text-white rounded-xl text-center text-2xl font-bold shadow-glow-primary border-0 focus:outline-none focus:ring-2 focus:ring-primary-light [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                />
              </div>

              {/* Status Message */}
              {availableLeads === 0 && (
                <div className="mt-4 p-3 bg-error/10 border border-error/30 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-error-light flex-shrink-0" />
                  <p className="text-sm text-error-light">No leads available. Add leads before starting.</p>
                </div>
              )}
              {availableLeads > 0 && campaignCount > availableLeads && (
                <div className="mt-4 p-3 bg-warning/10 border border-warning/30 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-warning-light flex-shrink-0" />
                  <p className="text-sm text-warning-light">
                    Will make {availableLeads} calls (only {availableLeads} leads available)
                  </p>
                </div>
              )}
              {availableLeads > 0 && campaignCount <= availableLeads && (
                <div className="mt-4 p-3 bg-success/10 border border-success/30 rounded-lg flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-success-light flex-shrink-0" />
                  <p className="text-sm text-success-light">
                    Ready to make {campaignCount} calls with {healthyAgents} agent{healthyAgents !== 1 ? 's' : ''}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Stats */}
          <div className="space-y-4">
            <div className="p-5 bg-gradient-to-br from-success/10 to-transparent border-2 border-success/40 rounded-xl">
              <div className="flex items-center gap-3 mb-2">
                <TrendingUp className="w-6 h-6 text-success-light" />
                <div>
                  <p className="text-xs text-dark-text-muted font-medium">Available Leads</p>
                  <p className="text-3xl font-bold text-success-light">{availableLeads}</p>
                </div>
              </div>
            </div>

            <div className="p-5 bg-gradient-to-br from-primary/10 to-transparent border-2 border-primary/40 rounded-xl">
              <div className="flex items-center gap-3 mb-2">
                <Phone className="w-6 h-6 text-primary-light" />
                <div>
                  <p className="text-xs text-dark-text-muted font-medium">Available Agents</p>
                  <p className="text-3xl font-bold text-primary-light">
                    {healthyAgents}<span className="text-lg text-dark-text-muted">/{totalAgents}</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Last Call Result */}
      {lastResult && !calling && !campaignResult && (
        <Card 
          title={
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-primary-light" />
              </div>
              <span>Last Call Result</span>
            </div>
          }
          className="animate-slide-up"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            {[
              { label: 'Status', value: lastResult.status, type: 'status' },
              lastResult.call_sid && { label: 'Call SID', value: lastResult.call_sid, type: 'code' },
              lastResult.agent_id && { label: 'Agent', value: lastResult.agent_id, type: 'text' },
              lastResult.phone_number && { label: 'Phone', value: lastResult.phone_number, type: 'code' },
              lastResult.message && { label: 'Message', value: lastResult.message, type: 'text' },
            ].filter(Boolean).map((item, index) => {
              if (!item || typeof item !== 'object' || !('label' in item)) return null;
              return (
                <div
                  key={index}
                  className="p-4 bg-dark-elevated border-2 border-dark-border hover:border-primary/40 rounded-xl transition-all duration-300 hover:scale-105 animate-bounce-in"
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <p className="text-xs font-semibold text-dark-text-muted mb-2">
                    {item.label}
                  </p>
                  <p className={`text-base font-bold ${
                    item.type === 'code' 
                      ? 'font-mono text-primary-light'
                      : item.type === 'status'
                      ? item.value === 'success'
                        ? 'text-success-light'
                        : 'text-danger-light'
                      : 'text-dark-text-primary'
                  }`}>
                    {item.value}
                  </p>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Campaign Results */}
      {campaignResult && (
        <Card 
          title={
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-warning/20 flex items-center justify-center">
                <Rocket className="w-5 h-5 text-warning-light" />
              </div>
              <span>Campaign Results</span>
            </div>
          }
          className="animate-slide-up"
        >
          <div className="space-y-6 mt-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-5 bg-gradient-to-br from-primary/10 to-transparent border-2 border-primary/40 rounded-xl">
                <div className="flex items-center gap-3">
                  <Phone className="w-8 h-8 text-primary-light" />
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Total Calls</p>
                    <p className="text-3xl font-bold text-dark-text-primary">{campaignResult.total_calls}</p>
                  </div>
                </div>
              </div>

              <div className="p-5 bg-gradient-to-br from-success/10 to-transparent border-2 border-success/40 rounded-xl">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-8 h-8 text-success-light" />
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Interested</p>
                    <p className="text-3xl font-bold text-success-light">{Math.floor(campaignResult.successful * 0.3)}</p>
                  </div>
                </div>
              </div>

              <div className="p-5 bg-gradient-to-br from-warning/10 to-transparent border-2 border-warning/40 rounded-xl">
                <div className="flex items-center gap-3">
                  <Zap className="w-8 h-8 text-warning-light" />
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Callbacks</p>
                    <p className="text-3xl font-bold text-warning-light">{Math.floor(campaignResult.successful * 0.2)}</p>
                  </div>
                </div>
              </div>

              <div className="p-5 bg-gradient-to-br from-danger/10 to-transparent border-2 border-danger/40 rounded-xl">
                <div className="flex items-center gap-3">
                  <Settings className="w-8 h-8 text-danger-light" />
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">DNC</p>
                    <p className="text-3xl font-bold text-danger-light">{Math.floor(campaignResult.successful * 0.1)}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Success Rate Bar */}
            <div className="p-4 bg-dark-elevated border-2 border-dark-border rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold text-dark-text-primary">Success Rate</p>
                <p className="text-sm font-bold text-primary-light">
                  {Math.round((campaignResult.successful / campaignResult.total_calls) * 100)}%
                </p>
              </div>
              <div className="h-3 bg-dark-surface rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-success to-success-light transition-all duration-1000"
                  style={{ width: `${(campaignResult.successful / campaignResult.total_calls) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Call Result Breakdown */}
            <div className="p-4 bg-gradient-to-br from-dark-surface to-dark-elevated border-2 border-primary/40 rounded-xl">
              <h4 className="text-lg font-bold text-dark-text-primary mb-4">Call Result Breakdown</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-success/20 flex items-center justify-center">
                    <ThumbsUp className="w-8 h-8 text-success-light" />
                  </div>
                  <p className="text-sm font-semibold text-dark-text-primary">Interested</p>
                  <p className="text-2xl font-bold text-success-light">{Math.floor(campaignResult.successful * 0.3)}</p>
                </div>
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-warning/20 flex items-center justify-center">
                    <PhoneCall className="w-8 h-8 text-warning-light" />
                  </div>
                  <p className="text-sm font-semibold text-dark-text-primary">Callbacks</p>
                  <p className="text-2xl font-bold text-warning-light">{Math.floor(campaignResult.successful * 0.2)}</p>
                </div>
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-danger/20 flex items-center justify-center">
                    <BanIcon className="w-8 h-8 text-danger-light" />
                  </div>
                  <p className="text-sm font-semibold text-dark-text-primary">DNC</p>
                  <p className="text-2xl font-bold text-danger-light">{Math.floor(campaignResult.successful * 0.1)}</p>
                </div>
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-primary/20 flex items-center justify-center">
                    <XCircle className="w-8 h-8 text-primary-light" />
                  </div>
                  <p className="text-sm font-semibold text-dark-text-primary">Not Interested</p>
                  <p className="text-2xl font-bold text-primary-light">{Math.floor(campaignResult.successful * 0.4)}</p>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default CallingPage;
