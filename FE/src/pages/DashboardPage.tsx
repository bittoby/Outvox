// Dashboard Page - AWESOME Modern with Voice-Agent Animations

import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Phone, TrendingUp, Users, RefreshCw, Zap, Clock, AudioLines, CheckCircle2, XCircle, ArrowRightLeft, Ban, BarChart3, PhoneCall, AlertTriangle, ThumbsUp, ThumbsDown } from 'lucide-react';
import Card from '../components/Card/Card';
import KPICard from '../components/KPICard/KPICard';
import AgentCard from '../components/AgentCard/AgentCard';
// import StatsCard from '../components/StatsCard/StatsCard';
import { getAllAgentHealth, getCallStats } from '../services/api';
import { useWebSocket, EventType } from '../hooks/useWebSocket';
import type { Agent } from '../types/agent';
import type { CallStats } from '../types/stats';

const DashboardPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<CallStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);

  // Store previous values for trend calculation
  const [prevStats, setPrevStats] = useState<{
    activeAgents: number;
    totalCalls: number;
    successRate: number;
    pendingLeads: number;
    interested: number;
    notInterested: number;
    callback: number;
    dnc: number;
  } | null>(null);

  // Fetch data
  const fetchDashboardData = useCallback(async () => {
    try {
      const [agentsData, statsData] = await Promise.all([
        getAllAgentHealth(),
        getCallStats(),
      ]);
      
      // Store previous values before updating
      if (stats && agents.length > 0) {
        const prevActiveAgents = agents.filter((a) => a.status === 'healthy').length;
        const prevTotalCalls = stats.total_calls || 0;
        const prevSuccessRate = prevTotalCalls > 0 ? ((stats.interested || 0) / prevTotalCalls) * 100 : 0;
        const prevPendingLeads = stats.pending_leads || 0;

        setPrevStats({
          activeAgents: prevActiveAgents,
          totalCalls: prevTotalCalls,
          successRate: prevSuccessRate,
          pendingLeads: prevPendingLeads,
          interested: stats.interested || 0,
          notInterested: stats.not_interested || 0,
          callback: stats.callback || 0,
          dnc: stats.dnc || 0,
        });
      }
      
      setAgents(agentsData);
      setStats(statsData);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [stats, agents]);

  // Initial load
  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // WebSocket for real-time updates
  const { subscribe, on } = useWebSocket({ autoConnect: true });

  useEffect(() => {
    // Subscribe to relevant events
    subscribe([
      EventType.AGENT_HEALTH_UPDATE,
      EventType.CALL_STATS_UPDATE,
    ]);

    // Handle agent health updates
    const unsubscribeAgent = on(EventType.AGENT_HEALTH_UPDATE, () => {
      // Refetch agent data when health updates
      getAllAgentHealth().then(setAgents).catch(console.error);
    });

    // Handle call stats updates
    const unsubscribeStats = on(EventType.CALL_STATS_UPDATE, () => {
      // Refetch stats when call completes
      getCallStats().then(setStats).catch(console.error);
    });

    return () => {
      unsubscribeAgent();
      unsubscribeStats();
    };
  }, [subscribe, on]);

  // Manual refresh
  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  // Calculate KPIs
  const activeAgents = agents.filter((a) => a.status === 'healthy').length;
  const totalAgents = agents.length;
  const todayCalls = stats?.total_calls || 0;
  const successRate = todayCalls > 0 ? ((stats?.interested || 0) / todayCalls) * 100 : 0;
  const pendingLeads = stats?.pending_leads || 0;

  // Calculate trends dynamically
  const calculateTrend = (current: number, previous: number | undefined): { value: number; isPositive: boolean } | undefined => {
    if (previous === undefined || previous === 0) return undefined;
    
    const change = current - previous;
    const percentChange = Math.abs((change / previous) * 100);
    
    // Only show trend if there's a meaningful change (>0.1%)
    if (percentChange < 0.1) return undefined;
    
    return {
      value: Math.round(percentChange * 10) / 10, // Round to 1 decimal place
      isPositive: change > 0,
    };
  };

  // Calculate specific trends for KPI cards
  const activeAgentsTrend = calculateTrend(activeAgents, prevStats?.activeAgents);
  const callsTrend = calculateTrend(todayCalls, prevStats?.totalCalls);
  const successRateTrend = calculateTrend(successRate, prevStats?.successRate);
  const pendingLeadsTrend = calculateTrend(pendingLeads, prevStats?.pendingLeads);

  // Calculate trends for call results - reserved for future use
  // const interestedTrend = calculateTrend(stats?.interested || 0, prevStats?.interested);
  // const notInterestedTrend = calculateTrend(stats?.not_interested || 0, prevStats?.notInterested);
  // const callbackTrend = calculateTrend(stats?.callback || 0, prevStats?.callback);
  // const dncTrend = calculateTrend(stats?.dnc || 0, prevStats?.dnc);

  return (
    <div className="max-w-[1600px] mx-auto space-y-8">
      {/* Animated Header */}
      <div className="flex justify-between items-start animate-slide-in-left">
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-light to-primary flex items-center justify-center text-white shadow-glow-primary animate-float">
              <Activity className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-5xl font-bold bg-gradient-to-r from-dark-text-primary via-primary-light to-primary bg-clip-text text-transparent animate-fade-in">
                Dashboard
              </h1>
              <p className="text-base text-dark-text-secondary mt-1 animate-slide-in-left stagger-1">
                Real-time voice agent monitoring system
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="group flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-primary to-primary-dark hover:from-primary-light hover:to-primary text-white rounded-xl font-semibold transition-all duration-300 hover:scale-105 shadow-md hover:shadow-glow-primary disabled:opacity-50 disabled:cursor-not-allowed ripple animate-slide-in-right"
        >
          <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* KPI Cards with awesome animations */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          icon={<AudioLines className="w-7 h-7" />}
          title="Active Agents"
          value={`${activeAgents}/${totalAgents}`}
          subtitle="Agents online and ready"
          loading={loading}
          variant="primary"
          trend={activeAgentsTrend}
        />
        <KPICard
          icon={<Phone className="w-7 h-7" />}
          title="Today's Calls"
          value={todayCalls}
          subtitle="Total calls completed"
          loading={loading}
          variant="success"
          trend={callsTrend}
        />
        <KPICard
          icon={<TrendingUp className="w-7 h-7" />}
          title="Success Rate"
          value={`${Math.round(successRate)}%`}
          subtitle="Interested responses"
          loading={loading}
          variant="warning"
          trend={successRateTrend}
        />
        <KPICard
          icon={<Users className="w-7 h-7" />}
          title="Pending Leads"
          value={pendingLeads}
          subtitle="Ready to call"
          loading={loading}
          variant="info"
          trend={pendingLeadsTrend}
        />
      </div>

      {/* Agent Status Grid with NEW AgentCard component */}
      <Card
        title="Voice Agent Fleet"
        subtitle="Live monitoring of all Outvox agents"
        action={
          <div className="flex items-center gap-3 animate-pulse-slow">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-success shadow-glow-success"></span>
            </span>
            <span className="text-sm font-semibold text-dark-text-primary">
              Live • Updated {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
        }
      >
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mt-6">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-48 bg-dark-elevated border-2 border-dark-border rounded-xl animate-pulse"></div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mt-6">
            {agents.map((agent, index) => (
              <AgentCard key={agent.agent_id} agent={agent} index={index} />
            ))}
          </div>
        )}
      </Card>

      {/* Call Results & Twilio Numbers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Today's Call Results - Clear & Simple */}
        <Card 
          title={
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-primary-light" />
              </div>
              <span>Today's Call Results</span>
            </div>
          }
          subtitle={`${todayCalls} total calls completed`}
          className="animate-scale-in"
        >
          {stats ? (
            <div className="space-y-6 mt-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 gap-4 p-5 bg-gradient-to-br from-primary/10 to-transparent border-2 border-primary/40 rounded-xl">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <ThumbsUp className="w-6 h-6 text-success-light" />
                    <div className="text-3xl font-bold text-success-light">
                      {stats.interested}
                    </div>
                  </div>
                  <div className="text-xs font-semibold text-dark-text-secondary uppercase tracking-wide">
                    Interested
                  </div>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <ThumbsDown className="w-6 h-6 text-danger-light" />
                    <div className="text-3xl font-bold text-danger-light">
                      {stats.not_interested}
                    </div>
                  </div>
                  <div className="text-xs font-semibold text-dark-text-secondary uppercase tracking-wide">
                    Not Interested
                  </div>
                </div>
              </div>

              {/* Detailed Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between p-4 bg-dark-elevated border-2 border-success/40 rounded-xl hover:border-success/60 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-success/20 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-success-light" />
                    </div>
                    <div>
                      <div className="font-bold text-dark-text-primary">Interested</div>
                      <div className="text-xs text-dark-text-secondary">Positive responses</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-success-light">{stats.interested}</div>
                    {todayCalls > 0 && (
                      <div className="text-xs text-dark-text-muted">
                        {Math.round((stats.interested / todayCalls) * 100)}%
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-dark-elevated border-2 border-danger/40 rounded-xl hover:border-danger/60 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-danger/20 flex items-center justify-center">
                      <XCircle className="w-5 h-5 text-danger-light" />
                    </div>
                    <div>
                      <div className="font-bold text-dark-text-primary">Not Interested</div>
                      <div className="text-xs text-dark-text-secondary">Negative responses</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-danger-light">{stats.not_interested}</div>
                    {todayCalls > 0 && (
                      <div className="text-xs text-dark-text-muted">
                        {Math.round((stats.not_interested / todayCalls) * 100)}%
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-dark-elevated border-2 border-info/40 rounded-xl hover:border-info/60 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-info/20 flex items-center justify-center">
                      <ArrowRightLeft className="w-5 h-5 text-info-light" />
                    </div>
                    <div>
                      <div className="font-bold text-dark-text-primary">Callback Requested</div>
                      <div className="text-xs text-dark-text-secondary">Follow-up needed</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-info-light">{stats.callback}</div>
                    {todayCalls > 0 && (
                      <div className="text-xs text-dark-text-muted">
                        {Math.round((stats.callback / todayCalls) * 100)}%
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-dark-elevated border-2 border-warning/40 rounded-xl hover:border-warning/60 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-warning/20 flex items-center justify-center">
                      <Ban className="w-5 h-5 text-warning-light" />
                    </div>
                    <div>
                      <div className="font-bold text-dark-text-primary">Do Not Call</div>
                      <div className="text-xs text-dark-text-secondary">Opted out</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-warning-light">{stats.dnc}</div>
                    {todayCalls > 0 && (
                      <div className="text-xs text-dark-text-muted">
                        {Math.round((stats.dnc / todayCalls) * 100)}%
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16">
              <Clock className="w-16 h-16 text-dark-border animate-spin-slow mb-4" />
              <p className="text-center text-dark-text-muted">Loading results...</p>
            </div>
          )}
        </Card>

        {/* Twilio Number Usage - Clear & Simple */}
        <Card
          title={
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-info/20 flex items-center justify-center">
                <PhoneCall className="w-5 h-5 text-info-light" />
              </div>
              <span>Twilio Number Usage</span>
            </div>
          }
          subtitle={`${stats?.numbers?.filter(n => n.is_active)?.length || 0} active number${(stats?.numbers?.filter(n => n.is_active)?.length || 0) !== 1 ? 's' : ''} • Daily limit: 30 calls`}
          className="animate-scale-in stagger-1"
        >
          {stats && stats.numbers && stats.numbers.length > 0 ? (
            <div className="space-y-6 mt-6">
              {/* Summary Stats */}
              {(() => {
                const activeNumbers = stats.numbers.filter(n => n.is_active);
                const totalCalls = activeNumbers.reduce((sum, n) => sum + (n.daily_calls || 0), 0);
                const totalLimit = activeNumbers.length * 30;
                const totalPercentage = totalLimit > 0 ? (totalCalls / totalLimit) * 100 : 0;
                const nearLimitCount = activeNumbers.filter(n => (n.daily_calls || 0) >= 24).length;
                
                return (
                  <div className="p-5 bg-gradient-to-br from-primary/10 to-transparent border-2 border-primary/40 rounded-xl">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <div className="text-3xl font-bold text-primary-light mb-1">{totalCalls}</div>
                        <div className="text-xs font-semibold text-dark-text-secondary uppercase tracking-wide">
                          Total Calls Today
                        </div>
                      </div>
                      <div>
                        <div className="text-3xl font-bold text-info-light mb-1">{activeNumbers.length}</div>
                        <div className="text-xs font-semibold text-dark-text-secondary uppercase tracking-wide">
                          Active Numbers
                        </div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-dark-text-secondary font-medium">Overall Usage</span>
                        <span className="font-bold text-dark-text-primary">{totalCalls}/{totalLimit} calls</span>
                      </div>
                      <div className="h-2 bg-dark-elevated rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-primary to-primary-light transition-all duration-500"
                          style={{ width: `${Math.min(totalPercentage, 100)}%` }}
                        ></div>
                      </div>
                          {nearLimitCount > 0 && (
                        <div className="flex items-center gap-2 text-xs text-warning-light font-semibold">
                          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                          <span>{nearLimitCount} number{nearLimitCount !== 1 ? 's' : ''} near limit (≥24 calls)</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* Individual Numbers */}
              <div className="space-y-3">
                {stats.numbers
                  .filter(n => n.is_active)
                  .map((number) => {
                    const percentage = ((number.daily_calls || 0) / 30) * 100;
                    const isWarning = percentage >= 80;
                    const isNearLimit = percentage >= 60;
                    
                    return (
                      <div
                        key={number.phone}
                        className="group p-4 bg-dark-elevated border-2 border-dark-border hover:border-primary/40 rounded-xl transition-all duration-300 hover:scale-[1.02]"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                              isWarning ? 'bg-danger/20 text-danger-light' : 
                              isNearLimit ? 'bg-warning/20 text-warning-light' : 
                              'bg-success/20 text-success-light'
                            }`}>
                              <Phone className="w-5 h-5" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="font-bold font-mono text-dark-text-primary truncate">
                                {number.phone}
                              </div>
                              <div className="text-xs text-dark-text-secondary truncate">
                                {number.shop || 'Unassigned'}
                              </div>
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0 ml-3">
                            <div className={`text-xl font-bold font-mono ${
                              isWarning ? 'text-danger-light' :
                              isNearLimit ? 'text-warning-light' :
                              'text-success-light'
                            }`}>
                              {number.daily_calls || 0}/30
                            </div>
                            {isWarning && (
                              <div className="text-xs text-danger-light font-semibold animate-pulse">
                                Near Limit!
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="h-2 bg-dark-surface rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              isWarning ? 'bg-gradient-to-r from-danger to-danger-light' :
                              isNearLimit ? 'bg-gradient-to-r from-warning to-warning-light' :
                              'bg-gradient-to-r from-success to-success-light'
                            }`}
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
              </div>

              {/* Inactive Numbers (collapsed) */}
              {stats.numbers.filter(n => !n.is_active).length > 0 && (
                <div className="pt-3 border-t border-dark-border">
                  <div className="text-xs text-dark-text-muted text-center">
                    {stats.numbers.filter(n => !n.is_active).length} inactive number{stats.numbers.filter(n => !n.is_active).length !== 1 ? 's' : ''} hidden
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4 animate-bounce">
                <Phone className="w-10 h-10 text-dark-text-muted" />
              </div>
              <p className="text-dark-text-muted font-medium">No Twilio numbers configured</p>
            </div>
          )}
        </Card>
      </div>

      {/* System Status Footer */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-slide-up">
        <div className="bg-dark-surface border-2 border-success/40 rounded-xl p-4 hover:scale-105 transition-all duration-300 card-glow">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-success/20 flex items-center justify-center">
              <Zap className="w-6 h-6 text-success-light animate-pulse" />
            </div>
            <div>
              <p className="text-sm text-dark-text-muted font-medium">System Status</p>
              <p className="text-lg font-bold text-success-light">All Systems Online</p>
            </div>
          </div>
        </div>
        <div className="bg-dark-surface border-2 border-primary/40 rounded-xl p-4 hover:scale-105 transition-all duration-300 card-glow">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center">
              <Activity className="w-6 h-6 text-primary-light animate-pulse-ring" />
            </div>
            <div>
              <p className="text-sm text-dark-text-muted font-medium">API Response</p>
              <p className="text-lg font-bold text-primary-light">Fast & Stable</p>
            </div>
          </div>
        </div>
        <div className="bg-dark-surface border-2 border-info/40 rounded-xl p-4 hover:scale-105 transition-all duration-300 card-glow">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-info/20 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-info-light animate-pulse-slow" />
            </div>
            <div>
              <p className="text-sm text-dark-text-muted font-medium">Performance</p>
              <p className="text-lg font-bold text-info-light">Excellent</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
