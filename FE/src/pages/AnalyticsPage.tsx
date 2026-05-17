// Analytics Page - Clear, Accurate & User-Friendly

import React, { useState, useEffect, useCallback } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Phone, 
  Users, 
  MessageSquare, 
  Mail, 
  Store as StoreIcon, 
  ChevronDown, 
  Check,
  Info,
  AlertCircle
} from 'lucide-react';
import Card from '../components/Card/Card';
import Badge from '../components/Badge/Badge';
import { getCallStats, getAllAgentHealth, getSmsTimeline, getStores } from '../services/api';
import { useWebSocket, EventType } from '../hooks/useWebSocket';
import type { CallStats } from '../types/stats';
import type { Agent } from '../types/agent';
import type { Store } from '../types/lead';

const AnalyticsPage: React.FC = () => {
  const [stats, setStats] = useState<CallStats | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [smsLoading, setSmsLoading] = useState(false);
  const [timeRange, setTimeRange] = useState('7d');
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);
  const [smsTimeline, setSmsTimeline] = useState<any>(null);
  const [isStoreDropdownOpen, setIsStoreDropdownOpen] = useState(false);

  // Store previous stats for trend calculation
  const [prevStats, setPrevStats] = useState<{
    totalCalls: number;
    successRate: number;
    conversionRate: number;
  } | null>(null);

  // Load stores on mount
  useEffect(() => {
    const loadStores = async () => {
      try {
        const storesData = await getStores();
        setStores(storesData);
      } catch (error) {
        console.error('Error loading stores:', error);
      }
    };
    loadStores();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (isStoreDropdownOpen && !target.closest('.store-filter-dropdown')) {
        setIsStoreDropdownOpen(false);
      }
    };
    
    if (isStoreDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isStoreDropdownOpen]);

  // Load SMS timeline when store or time range changes
  useEffect(() => {
    const loadSmsTimeline = async () => {
      try {
        setSmsLoading(true);
        // Calculate date range based on timeRange
        const endDate = new Date();
        const startDate = new Date();
        
        if (timeRange === '24h') {
          startDate.setDate(startDate.getDate() - 1);
        } else if (timeRange === '7d') {
          startDate.setDate(startDate.getDate() - 7);
        } else if (timeRange === '30d') {
          startDate.setDate(startDate.getDate() - 30);
        } else {
          startDate.setDate(startDate.getDate() - 90); // All = last 90 days
        }

        const formatDate = (date: Date) => date.toISOString().split('T')[0];
        
        const timelineData = await getSmsTimeline(
          selectedStoreId || undefined,
          formatDate(startDate),
          formatDate(endDate)
        );
        setSmsTimeline(timelineData);
      } catch (error) {
        console.error('Error loading SMS timeline:', error);
        setSmsTimeline(null);
      } finally {
        setSmsLoading(false);
      }
    };

    loadSmsTimeline();
  }, [selectedStoreId, timeRange]);

  // Load call stats and agents
  const fetchStats = useCallback(async (isRefresh: boolean = false) => {
    try {
      // Only show loading spinner on initial load, not on auto-refresh
      if (!isRefresh && isInitialLoad) {
        setLoading(true);
      }
      
      const [statsData, agentsData] = await Promise.all([
        getCallStats(),
        getAllAgentHealth(),
      ]);

      // Store previous values before updating for trend calculation
      if (stats) {
        const prevTotalCalls = stats.total_calls || 0;
        const prevSuccessRate = prevTotalCalls > 0 ? ((stats.interested || 0) / prevTotalCalls) * 100 : 0;
        const prevConversionRate = prevTotalCalls > 0 ? (((stats.interested || 0) + (stats.callback || 0)) / prevTotalCalls) * 100 : 0;

        setPrevStats({
          totalCalls: prevTotalCalls,
          successRate: prevSuccessRate,
          conversionRate: prevConversionRate,
        });
      }

      setStats(statsData);
      setAgents(agentsData);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
      setIsInitialLoad(false);
    }
  }, [stats, isInitialLoad]);

  useEffect(() => {
    fetchStats(false); // Initial load
  }, [fetchStats]);

  // WebSocket for real-time updates
  const { subscribe, on } = useWebSocket({ autoConnect: true });

  useEffect(() => {
    // Subscribe to stats and SMS updates
    subscribe([
      EventType.CALL_STATS_UPDATE,
      EventType.AGENT_HEALTH_UPDATE,
      EventType.SMS_RECEIVED,
      EventType.SMS_SENT,
    ]);

    // Handle call stats updates
    const unsubscribeStats = on(EventType.CALL_STATS_UPDATE, () => {
      fetchStats(true);
    });

    // Handle agent health updates
    const unsubscribeAgents = on(EventType.AGENT_HEALTH_UPDATE, () => {
      getAllAgentHealth().then(setAgents).catch(console.error);
    });

    // Handle SMS received - refresh SMS timeline
    const unsubscribeSMSReceived = on(EventType.SMS_RECEIVED, () => {
      // Reload SMS timeline when SMS is received
      const loadSmsTimeline = async () => {
        try {
          const endDate = new Date();
          const startDate = new Date();
          
          if (timeRange === '24h') {
            startDate.setDate(startDate.getDate() - 1);
          } else if (timeRange === '7d') {
            startDate.setDate(startDate.getDate() - 7);
          } else if (timeRange === '30d') {
            startDate.setDate(startDate.getDate() - 30);
          } else {
            startDate.setDate(startDate.getDate() - 90);
          }

          const formatDate = (date: Date) => date.toISOString().split('T')[0];
          const timelineData = await getSmsTimeline(
            selectedStoreId || undefined,
            formatDate(startDate),
            formatDate(endDate)
          );
          setSmsTimeline(timelineData);
        } catch (error) {
          console.error('Error reloading SMS timeline:', error);
        }
      };
      loadSmsTimeline();
    });

    // Handle SMS sent - refresh SMS timeline
    const unsubscribeSMSSent = on(EventType.SMS_SENT, () => {
      // Reload SMS timeline when SMS is sent
      const loadSmsTimeline = async () => {
        try {
          const endDate = new Date();
          const startDate = new Date();
          
          if (timeRange === '24h') {
            startDate.setDate(startDate.getDate() - 1);
          } else if (timeRange === '7d') {
            startDate.setDate(startDate.getDate() - 7);
          } else if (timeRange === '30d') {
            startDate.setDate(startDate.getDate() - 30);
          } else {
            startDate.setDate(startDate.getDate() - 90);
          }

          const formatDate = (date: Date) => date.toISOString().split('T')[0];
          const timelineData = await getSmsTimeline(
            selectedStoreId || undefined,
            formatDate(startDate),
            formatDate(endDate)
          );
          setSmsTimeline(timelineData);
        } catch (error) {
          console.error('Error reloading SMS timeline:', error);
        }
      };
      loadSmsTimeline();
    });

    return () => {
      unsubscribeStats();
      unsubscribeAgents();
      unsubscribeSMSReceived();
      unsubscribeSMSSent();
    };
  }, [subscribe, on, fetchStats, timeRange, selectedStoreId]);

  // No polling - only real-time updates via WebSocket

  // Calculate real metrics from actual data
  const totalCalls = stats?.total_calls || 0;
  const interestedCalls = stats?.interested || 0;
  const notInterestedCalls = stats?.not_interested || 0;
  const callbackCalls = stats?.callback || 0;
  const dncCalls = stats?.dnc || 0;
  // const pendingLeads = stats?.pending_leads || 0; // Reserved for future use

  // Calculate rates
  const successRate = totalCalls > 0 ? ((interestedCalls / totalCalls) * 100) : 0;
  const conversionRate = totalCalls > 0 ? (((interestedCalls + callbackCalls) / totalCalls) * 100) : 0;
  const dncRate = totalCalls > 0 ? ((dncCalls / totalCalls) * 100) : 0;

  // Calculate trends (comparing current vs previous fetch)
  const calculateTrend = (current: number, previous: number | undefined): { value: string; isPositive: boolean } => {
    if (previous === undefined || previous === 0) {
      if (current > 0) return { value: 'New', isPositive: true };
      return { value: '0.0', isPositive: true };
    }
    
    const change = current - previous;
    const percentChange = (change / previous) * 100;
    
    return {
      value: Math.abs(percentChange).toFixed(1),
      isPositive: percentChange >= 0,
    };
  };

  const callsTrend = calculateTrend(totalCalls, prevStats?.totalCalls);
  const successTrend = calculateTrend(successRate, prevStats?.successRate);
  const conversionTrend = calculateTrend(conversionRate, prevStats?.conversionRate);

  // Real agent performance (using actual call counts)
  const agentPerformance = agents
    .map((agent) => ({
      id: agent.agent_id,
      calls: agent.total_calls || 0,
      status: agent.status,
    }))
    .filter((agent) => agent.calls > 0)
    .sort((a, b) => b.calls - a.calls)
    .slice(0, 10);

  // SMS metrics from timeline
  const totalSms = smsTimeline?.timeline?.reduce((sum: number, day: any) => sum + (day.sms_sent || 0), 0) || 0;
  const totalReplies = smsTimeline?.timeline?.reduce((sum: number, day: any) => sum + (day.replies_received || 0), 0) || 0;
  const smsReplyRate = totalSms > 0 ? Math.round((totalReplies / totalSms) * 100) : 0;

  return (
    <div className="max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-slide-in-left">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-white shadow-glow-primary animate-float">
            <BarChart3 className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-primary-light to-primary bg-clip-text text-transparent">
              Analytics Dashboard
            </h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              Real-time performance metrics and insights
            </p>
          </div>
        </div>

        {/* Time Range Selector - Only affects SMS Timeline */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-dark-surface border-2 border-dark-border rounded-lg p-1">
            {['24h', '7d', '30d', 'All'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range.toLowerCase())}
                className={`px-4 py-2 rounded-md text-sm font-semibold transition-all ${
                  timeRange === range.toLowerCase()
                    ? 'bg-primary text-white shadow-sm'
                    : 'text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated'
                }`}
                title="Time range for SMS metrics"
              >
                {range}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-info/10 border-2 border-info/30 rounded-xl p-4 flex items-start gap-3 animate-slide-in-left">
        <Info className="w-5 h-5 text-info-light flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-dark-text-primary mb-1">About This Dashboard</p>
          <p className="text-xs text-dark-text-secondary">
            <strong>Call Metrics:</strong> Shows today's statistics (real-time updates via WebSocket). 
            <strong> SMS Metrics:</strong> Filter by store and time range using the controls above. 
            All data is real-time and based on actual system activity.
          </p>
        </div>
      </div>

      {/* CALL METRICS SECTION */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Phone className="w-6 h-6 text-primary-light" />
          <h2 className="text-2xl font-bold text-dark-text-primary">Call Performance</h2>
          <Badge variant="info" size="sm">Today's Data</Badge>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-dark-surface border-2 border-dark-border rounded-xl p-5 animate-pulse">
                <div className="h-10 w-10 rounded-lg bg-dark-elevated mb-3"></div>
                <div className="h-4 w-24 bg-dark-elevated rounded mb-2"></div>
                <div className="h-8 w-16 bg-dark-elevated rounded"></div>
              </div>
            ))}
          </div>
        ) : (
          <>
            {/* Key Call Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-dark-surface border-2 border-dark-border hover:border-primary/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Phone className="w-5 h-5 text-primary-light" />
                  </div>
                  {prevStats && parseFloat(callsTrend.value) > 0 && callsTrend.value !== 'New' && (
                    <div className={`text-xs font-bold px-2 py-1 rounded ${
                      callsTrend.isPositive ? 'text-success bg-success/10' : 'text-danger bg-danger/10'
                    }`}>
                      {callsTrend.isPositive ? '↑' : '↓'} {callsTrend.value}%
                    </div>
                  )}
                </div>
                <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-1">
                  Total Calls
                </p>
                <p className="text-3xl font-bold text-dark-text-primary">{totalCalls.toLocaleString()}</p>
                <p className="text-xs text-dark-text-muted mt-1">All calls made today</p>
              </div>

              <div className="bg-dark-surface border-2 border-dark-border hover:border-success/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-1">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-success-light" />
                  </div>
                  {prevStats && parseFloat(successTrend.value) > 0 && successTrend.value !== 'New' && (
                    <div className={`text-xs font-bold px-2 py-1 rounded ${
                      successTrend.isPositive ? 'text-success bg-success/10' : 'text-danger bg-danger/10'
                    }`}>
                      {successTrend.isPositive ? '↑' : '↓'} {successTrend.value}%
                    </div>
                  )}
                </div>
                <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-1">
                  Success Rate
                </p>
                <p className="text-3xl font-bold text-dark-text-primary">{Math.round(successRate)}%</p>
                <p className="text-xs text-dark-text-muted mt-1">
                  {interestedCalls} interested out of {totalCalls || 'N/A'} calls
                </p>
              </div>

              <div className="bg-dark-surface border-2 border-dark-border hover:border-info/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-2">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
                    <Users className="w-5 h-5 text-info-light" />
                  </div>
                  {prevStats && parseFloat(conversionTrend.value) > 0 && conversionTrend.value !== 'New' && (
                    <div className={`text-xs font-bold px-2 py-1 rounded ${
                      conversionTrend.isPositive ? 'text-success bg-success/10' : 'text-danger bg-danger/10'
                    }`}>
                      {conversionTrend.isPositive ? '↑' : '↓'} {conversionTrend.value}%
                    </div>
                  )}
                </div>
                <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-1">
                  Conversion Rate
                </p>
                <p className="text-3xl font-bold text-dark-text-primary">{Math.round(conversionRate)}%</p>
                <p className="text-xs text-dark-text-muted mt-1">
                  Interested + Callbacks
                </p>
              </div>

              <div className="bg-dark-surface border-2 border-dark-border hover:border-warning/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-3">
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
                    <AlertCircle className="w-5 h-5 text-warning-light" />
                  </div>
                </div>
                <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-1">
                  DNC Rate
                </p>
                <p className="text-3xl font-bold text-dark-text-primary">{Math.round(dncRate)}%</p>
                <p className="text-xs text-dark-text-muted mt-1">
                  {dncCalls} do not call requests
                </p>
              </div>
            </div>

            {/* Call Results Breakdown */}
            <Card 
              title="Call Results Breakdown" 
              subtitle="Distribution of today's call outcomes"
              className="animate-scale-in"
            >
              <div className="space-y-4 mt-6">
                {[
                  { 
                    label: 'Interested', 
                    value: interestedCalls, 
                    color: 'success', 
                    total: totalCalls,
                    description: 'Leads who expressed interest'
                  },
                  { 
                    label: 'Callback Requested', 
                    value: callbackCalls, 
                    color: 'info', 
                    total: totalCalls,
                    description: 'Leads who want a callback'
                  },
                  { 
                    label: 'Not Interested', 
                    value: notInterestedCalls, 
                    color: 'neutral', 
                    total: totalCalls,
                    description: 'Leads who declined'
                  },
                  { 
                    label: 'Do Not Call', 
                    value: dncCalls, 
                    color: 'warning', 
                    total: totalCalls,
                    description: 'Leads marked as DNC'
                  },
                ].map((item, index) => {
                  const percentage = item.total > 0 ? Math.round((item.value / item.total) * 100) : 0;
                  const colorClasses = {
                    success: 'bg-success',
                    info: 'bg-info',
                    warning: 'bg-warning',
                    neutral: 'bg-dark-elevated',
                  };
                  return (
                    <div key={item.label} className="animate-slide-in-left" style={{ animationDelay: `${index * 0.1}s` }}>
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <span className="text-sm font-semibold text-dark-text-primary">{item.label}</span>
                          <p className="text-xs text-dark-text-muted mt-0.5">{item.description}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-dark-text-primary">{item.value.toLocaleString()}</span>
                          <span className="text-xs text-dark-text-muted">({percentage}%)</span>
                        </div>
                      </div>
                      <div className="h-3 bg-dark-elevated rounded-full overflow-hidden">
                        <div
                          className={`h-full ${colorClasses[item.color as keyof typeof colorClasses]} rounded-full transition-all duration-1000`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Agent Performance */}
            <Card 
              title="Agent Performance" 
              subtitle="Top agents by call volume"
              className="animate-scale-in"
            >
              {agentPerformance.length > 0 ? (
                <div className="space-y-3 mt-6">
                  {agentPerformance.map((agent, index) => (
                    <div
                      key={agent.id}
                      className="flex items-center justify-between p-3 bg-dark-elevated hover:bg-dark-surface border border-dark-border hover:border-primary/30 rounded-lg transition-all duration-200 animate-slide-in-right"
                      style={{ animationDelay: `${index * 0.05}s` }}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                          <span className="text-xs font-bold text-primary-light">#{index + 1}</span>
                        </div>
                        <div>
                          <p className="text-sm font-bold text-dark-text-primary">{agent.id}</p>
                          <p className="text-xs text-dark-text-muted">
                            {agent.calls} call{agent.calls !== 1 ? 's' : ''} • {agent.status}
                          </p>
                        </div>
                      </div>
                      <Badge 
                        variant={agent.status === 'healthy' ? 'success' : agent.status === 'idle' ? 'warning' : 'neutral'} 
                        size="sm"
                      >
                        {agent.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Users className="w-12 h-12 text-dark-border mb-3" />
                  <p className="text-sm font-semibold text-dark-text-primary mb-1">No Agent Data</p>
                  <p className="text-xs text-dark-text-muted">Agents will appear here once they make calls</p>
                </div>
              )}
            </Card>
          </>
        )}
      </div>

      {/* SMS METRICS SECTION */}
      <div className="space-y-4 mt-8">
        <div className="flex items-center gap-3">
          <MessageSquare className="w-6 h-6 text-primary-light" />
          <h2 className="text-2xl font-bold text-dark-text-primary">SMS Campaign Performance</h2>
        </div>

        {/* Store Filter for SMS Metrics */}
        <Card variant="primary" className="animate-slide-in-left">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                <StoreIcon className="w-5 h-5 text-primary-light" />
              </div>
              <label className="text-dark-text-primary font-semibold whitespace-nowrap">
                Filter by Store:
              </label>
            </div>
            <div className="flex-1 w-full sm:max-w-md relative store-filter-dropdown">
              <button
                type="button"
                onClick={() => setIsStoreDropdownOpen(!isStoreDropdownOpen)}
                className="w-full px-4 py-3 pl-4 pr-10 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary-light focus:outline-none transition-all duration-300 hover:border-primary/50 font-medium shadow-sm hover:shadow-md text-left flex items-center justify-between cursor-pointer"
              >
                <span className="truncate">
                  {selectedStoreId 
                    ? stores.find(s => s.store_id === selectedStoreId)?.name || 'All Stores'
                    : 'All Stores'}
                </span>
                <ChevronDown 
                  className={`w-4 h-4 text-dark-text-muted transition-transform duration-300 flex-shrink-0 ${
                    isStoreDropdownOpen ? 'rotate-180' : ''
                  }`} 
                />
              </button>
              
              {/* Custom Dropdown */}
              {isStoreDropdownOpen && (
                <div className="absolute z-50 w-full mt-2 bg-dark-elevated border-2 border-dark-border rounded-lg shadow-xl max-h-64 overflow-y-auto animate-scale-in">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedStoreId(null);
                      setIsStoreDropdownOpen(false);
                    }}
                    className={`w-full px-4 py-3 text-left hover:bg-primary/10 transition-colors duration-200 flex items-center justify-between group ${
                      !selectedStoreId 
                        ? 'bg-primary/5 border-l-2 border-primary-light' 
                        : ''
                    }`}
                  >
                    <div className="font-medium text-dark-text-primary group-hover:text-primary-light transition-colors">
                      All Stores
                    </div>
                    {!selectedStoreId && (
                      <Check className="w-4 h-4 text-primary-light flex-shrink-0 ml-2" />
                    )}
                  </button>
                  {stores.map((store) => (
                    <button
                      key={store.store_id}
                      type="button"
                      onClick={() => {
                        setSelectedStoreId(store.store_id);
                        setIsStoreDropdownOpen(false);
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-primary/10 transition-colors duration-200 flex items-center justify-between group ${
                        selectedStoreId === store.store_id 
                          ? 'bg-primary/5 border-l-2 border-primary-light' 
                          : ''
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-dark-text-primary group-hover:text-primary-light transition-colors">
                          {store.name}
                        </div>
                        <div className="text-xs text-dark-text-muted mt-0.5 truncate">
                          {store.location}
                        </div>
                      </div>
                      {selectedStoreId === store.store_id && (
                        <Check className="w-4 h-4 text-primary-light flex-shrink-0 ml-2" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* SMS Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-dark-surface border-2 border-dark-border hover:border-primary/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left">
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Mail className="w-5 h-5 text-primary-light" />
              </div>
            </div>
            <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-1">SMS Sent</p>
            <p className="text-3xl font-bold text-dark-text-primary">{totalSms.toLocaleString()}</p>
            <p className="text-xs text-dark-text-muted mt-1">Total messages sent in selected period</p>
          </div>

          <div className="bg-dark-surface border-2 border-dark-border hover:border-success/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-1">
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-success-light" />
              </div>
            </div>
            <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-1">Positive Replies</p>
            <p className="text-3xl font-bold text-dark-text-primary">{totalReplies.toLocaleString()}</p>
            <p className="text-xs text-dark-text-muted mt-1">YES replies received (positive responses)</p>
          </div>

          <div className="bg-dark-surface border-2 border-dark-border hover:border-info/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-2">
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-info-light" />
              </div>
            </div>
            <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-1">Positive Reply Rate</p>
            <p className="text-3xl font-bold text-dark-text-primary">{smsReplyRate}%</p>
            <p className="text-xs text-dark-text-muted mt-1">
              {totalSms > 0 ? `${totalReplies} YES replies of ${totalSms} messages` : 'No data'}
            </p>
          </div>
        </div>

        {/* SMS Timeline Chart */}
        <Card 
          title="SMS Activity Timeline" 
          subtitle={`Daily SMS activity for ${timeRange === 'all' ? 'last 90 days' : timeRange}`}
          className="animate-scale-in"
        >
          {smsLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-sm text-dark-text-muted">Loading SMS data...</p>
              </div>
            </div>
          ) : smsTimeline?.timeline && smsTimeline.timeline.length > 0 ? (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-dark-border">
                    <th className="text-left py-3 px-4 font-semibold text-dark-text-primary">Date</th>
                    <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">SMS Sent</th>
                    <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Positive Replies</th>
                    <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Positive Reply Rate</th>
                    <th className="text-left py-3 px-4 font-semibold text-dark-text-primary">Activity</th>
                  </tr>
                </thead>
                <tbody>
                  {smsTimeline.timeline.map((day: any, index: number) => {
                    const maxValue = Math.max(
                      ...smsTimeline.timeline.map((d: any) => Math.max(d.sms_sent || 0, d.replies_received || 0))
                    );
                    const smsPercent = maxValue > 0 ? ((day.sms_sent || 0) / maxValue) * 100 : 0;
                    const replyPercent = maxValue > 0 ? ((day.replies_received || 0) / maxValue) * 100 : 0;
                    const replyRate = (day.sms_sent || 0) > 0 
                      ? Math.round(((day.replies_received || 0) / (day.sms_sent || 1)) * 100) 
                      : 0;
                    
                    // Format date to be more readable
                    const dateObj = new Date(day.date);
                    const formattedDate = dateObj.toLocaleDateString('en-US', { 
                      month: 'short', 
                      day: 'numeric',
                      year: dateObj.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
                    });
                    
                    return (
                      <tr 
                        key={day.date}
                        className="border-b border-dark-border hover:bg-dark-elevated transition-colors duration-200 animate-slide-in-left"
                        style={{ animationDelay: `${index * 0.03}s` }}
                      >
                        <td className="py-3 px-4">
                          <div className="font-semibold text-dark-text-primary">{formattedDate}</div>
                          <div className="text-xs text-dark-text-muted mt-0.5">
                            {dateObj.toLocaleDateString('en-US', { weekday: 'short' })}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-primary"></div>
                            <span className="font-bold text-dark-text-primary">{day.sms_sent || 0}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-success"></div>
                            <span className="font-bold text-success-light">{day.replies_received || 0}</span>
                            <span className="text-xs text-dark-text-muted">(YES)</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className={`font-bold ${
                            replyRate >= 20 ? 'text-success-light' : 
                            replyRate >= 10 ? 'text-warning-light' : 
                            'text-dark-text-muted'
                          }`}>
                            {replyRate}%
                          </span>
                          <div className="text-xs text-dark-text-muted mt-0.5">Positive</div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="space-y-1.5">
                            {/* SMS Sent Bar */}
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-dark-text-muted w-16">SMS:</span>
                              <div className="flex-1 h-2 bg-dark-surface rounded-full overflow-hidden border border-dark-border">
                                <div 
                                  className="h-full bg-gradient-to-r from-primary to-primary-light transition-all duration-700 rounded-full"
                                  style={{ width: `${Math.min(smsPercent, 100)}%` }}
                                />
                              </div>
                            </div>
                            {/* Replies Bar */}
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-dark-text-muted w-16">Replies:</span>
                              <div className="flex-1 h-2 bg-dark-surface rounded-full overflow-hidden border border-dark-border">
                                <div 
                                  className="h-full bg-gradient-to-r from-success to-success-light transition-all duration-700 rounded-full"
                                  style={{ width: `${Math.min(replyPercent, 100)}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4">
                <MessageSquare className="w-10 h-10 text-dark-text-muted" />
              </div>
              <h3 className="text-lg font-bold text-dark-text-primary mb-2">No SMS Data Available</h3>
              <p className="text-sm text-dark-text-muted text-center max-w-md">
                No SMS activity found for the selected time period{selectedStoreId ? ' and store' : ''}. 
                Try selecting a different time range or store filter.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default AnalyticsPage;
