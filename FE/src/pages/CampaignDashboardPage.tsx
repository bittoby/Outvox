// Campaign Dashboard Page - Milestone 13
import React, { useState, useEffect, useCallback } from 'react';
import { 
  MessageSquare, 
  Phone, 
  Store as StoreIcon, 
  Rocket, 
  Activity,
  AlertCircle,
  CheckCircle2,
  CheckCircle,
  XCircle,
  BarChart3,
  Pause,
  Play,
  PhoneOff,
  ChevronDown,
  ChevronUp,
  Check,
  Trash2,
  Users,
  Clock
} from 'lucide-react';
import Card from '../components/Card/Card';
import KPICard from '../components/KPICard/KPICard';
import Button from '../components/Button/Button';
import Badge from '../components/Badge/Badge';
import CampaignPreviewModal from '../components/CampaignPreviewModal/CampaignPreviewModal';
import {
  getCampaigns,
  getStorePhoneNumbers,
  getStoreDailyStats,
  getStores,
  pauseCampaign,
  resumeCampaign,
  deleteCampaign,
  getCampaignDetails,
  getBatchLeads,
} from '../services/api';
import { useWebSocket, EventType } from '../hooks/useWebSocket';
import type { Campaign, PhoneNumberHealth, StoreDailyStats, StartCampaignResponse } from '../types/campaign';
import type { Store } from '../types/lead';

const CampaignDashboardPage: React.FC = () => {
  // State management
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumberHealth[]>([]);
  const [dailyStats, setDailyStats] = useState<StoreDailyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedCampaignDetails, setSelectedCampaignDetails] = useState<any>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [expandedBatchId, setExpandedBatchId] = useState<number | null>(null);
  const [batchLeads, setBatchLeads] = useState<any>(null);
  const [loadingBatchLeads, setLoadingBatchLeads] = useState(false);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (isDropdownOpen && !target.closest('.store-selector-dropdown')) {
        setIsDropdownOpen(false);
      }
    };
    
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isDropdownOpen]);

  const loadStores = useCallback(async () => {
    try {
      const storesData = await getStores();
      setStores(storesData);
      if (storesData.length > 0) {
        setSelectedStoreId(current => current ?? storesData[0].store_id);
      }
    } catch (error) {
      console.error('Error loading stores:', error);
    }
  }, []);

  // Load stores on mount
  useEffect(() => {
    loadStores();
  }, [loadStores]);

  const loadStoreData = useCallback(async (isRefresh: boolean = false) => {
    if (!selectedStoreId) return;

    // Show loading for initial load or when switching stores
    if (!isRefresh) {
      setLoading(true);
    }
    
    try {
      const [campaignsData, phoneData, statsData] = await Promise.all([
        getCampaigns(selectedStoreId),
        getStorePhoneNumbers(selectedStoreId),
        getStoreDailyStats(selectedStoreId),
      ]);

      setCampaigns(campaignsData);
      setPhoneNumbers(phoneData?.phone_numbers || []);
      setDailyStats(statsData);
    } catch (error) {
      console.error('Error loading store data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedStoreId]);

  // Load data when store is selected
  useEffect(() => {
    if (selectedStoreId) {
      setLoading(true); // Set loading immediately when store changes
      loadStoreData(false);
    }
  }, [selectedStoreId, loadStoreData]);

  // WebSocket for real-time updates
  const { subscribe, on } = useWebSocket({ autoConnect: true });

  useEffect(() => {
    if (!selectedStoreId) return;

    // Subscribe to campaign events
    subscribe([
      EventType.CAMPAIGN_PROGRESS,
      EventType.CAMPAIGN_CREATED,
      EventType.CAMPAIGN_UPDATED,
      EventType.STORE_STATS_UPDATE,
    ]);

    // Handle campaign progress - update campaign in real-time from WebSocket data
    const unsubscribeProgress = on(EventType.CAMPAIGN_PROGRESS, (data: any) => {
      console.log('📡 Campaign progress received:', data);
      
      // Only update if this is for the selected store
      if (data.store_id && data.store_id !== selectedStoreId) {
        return;
      }
      
      // Update the specific campaign in state directly for instant UI update
      if (data.campaign_id) {
        setCampaigns(prevCampaigns => 
          prevCampaigns.map(campaign => 
            campaign.campaign_id === data.campaign_id
              ? {
                  ...campaign,
                  actual_sent: data.campaign_actual_sent ?? campaign.actual_sent,
                  status: data.campaign_status ?? campaign.status,
                  progress_percentage: data.progress_percentage ?? campaign.progress_percentage,
                  completed_batches: data.completed_batches ?? campaign.completed_batches,
                  pending_batches: data.pending_batches ?? campaign.pending_batches,
                }
              : campaign
          )
        );
      }
      
      // Also refresh full data to ensure consistency
      loadStoreData(true);
    });

    // Handle campaign created
    const unsubscribeCreated = on(EventType.CAMPAIGN_CREATED, () => {
      loadStoreData(true);
    });

    // Handle campaign updated
    const unsubscribeUpdated = on(EventType.CAMPAIGN_UPDATED, () => {
      loadStoreData(true);
    });

    // Handle store stats update
    const unsubscribeStats = on(EventType.STORE_STATS_UPDATE, () => {
      loadStoreData(true);
    });

    return () => {
      unsubscribeProgress();
      unsubscribeCreated();
      unsubscribeUpdated();
      unsubscribeStats();
    };
  }, [selectedStoreId, subscribe, on, loadStoreData]);

  const selectedStore = stores.find((s) => s.store_id === selectedStoreId);
  // Show all campaigns - no filtering needed
  const allCampaigns = campaigns;

  // Calculate progress percentages
  const smsProgress = selectedStore
    ? ((dailyStats?.sms_sent_today || 0) / selectedStore.daily_sms_quota) * 100
    : 0;
  const callProgress = selectedStore
    ? ((dailyStats?.calls_made_today || 0) / selectedStore.daily_call_quota) * 100
    : 0;

  // Handle campaign pause
  const handlePauseCampaign = async (campaignId: number) => {
    try {
      await pauseCampaign(campaignId);
      // Refresh campaigns silently (no loading state)
      loadStoreData(true);
      alert('✅ Campaign paused successfully');
    } catch (error) {
      console.error('Error pausing campaign:', error);
      alert('❌ Failed to pause campaign');
    }
  };

  // Handle campaign resume
  const handleResumeCampaign = async (campaignId: number) => {
    try {
      await resumeCampaign(campaignId);
      // Refresh campaigns silently (no loading state)
      loadStoreData(true);
      alert('✅ Campaign resumed successfully');
    } catch (error) {
      console.error('Error resuming campaign:', error);
      alert('❌ Failed to resume campaign');
    }
  };

  // Handle campaign delete
  const handleDeleteCampaign = async (campaignId: number) => {
    const confirmed = window.confirm(
      `⚠️ Are you sure you want to delete Campaign #${campaignId}?\n\n` +
      `This will permanently delete:\n` +
      `- The campaign record\n` +
      `- All scheduled batches\n` +
      `- All batch-lead mappings\n\n` +
      `This action cannot be undone!`
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteCampaign(campaignId);
      // Refresh campaigns silently (no loading state)
      loadStoreData(true);
      alert(`✅ Campaign #${campaignId} deleted successfully`);
    } catch (error: any) {
      console.error('Error deleting campaign:', error);
      const errorMessage = error?.message || 'Failed to delete campaign';
      alert(`❌ ${errorMessage}`);
    }
  };

  // View campaign details - opens modal with batch info and loads failed leads
  const viewCampaignDetails = async (campaignId: number) => {
    setLoadingDetails(true);
    setShowDetailsModal(true);
    setExpandedBatchId(null);
    setBatchLeads(null);
    try {
      const details = await getCampaignDetails(campaignId);
      if (!details) {
        alert('❌ Failed to load campaign details');
        setShowDetailsModal(false);
        return;
      }
      setSelectedCampaignDetails(details);
      
      // Auto-load failed leads for the first batch that has failures
      console.log('[CampaignDetails] Batches:', details.batches);
      if (details.batches && details.batches.length > 0) {
        const firstBatchWithFailures = details.batches.find(
          (b: any) => (b.target_count || 25) - (b.actual_sent || 0) > 0
        );
        console.log('[CampaignDetails] First batch with failures:', firstBatchWithFailures);
        if (firstBatchWithFailures) {
          // Auto-expand the first batch with failures
          setExpandedBatchId(firstBatchWithFailures.batch_id);
          try {
            console.log('[CampaignDetails] Loading batch leads for batch:', firstBatchWithFailures.batch_id);
            const leads = await getBatchLeads(firstBatchWithFailures.batch_id);
            console.log('[CampaignDetails] Batch leads loaded:', leads);
            setBatchLeads(leads);
          } catch (e) {
            console.error('Error auto-loading batch leads:', e);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching campaign details:', error);
      alert('❌ Failed to load campaign details');
      setShowDetailsModal(false);
    } finally {
      setLoadingDetails(false);
    }
  };

  // Load leads for a specific batch (to show per-lead failure reasons)
  const loadBatchLeads = async (batchId: number) => {
    if (expandedBatchId === batchId) {
      // Collapse if already expanded
      setExpandedBatchId(null);
      setBatchLeads(null);
      return;
    }
    
    setLoadingBatchLeads(true);
    setExpandedBatchId(batchId);
    try {
      const leads = await getBatchLeads(batchId);
      setBatchLeads(leads);
    } catch (error) {
      console.error('Error fetching batch leads:', error);
      setBatchLeads(null);
    } finally {
      setLoadingBatchLeads(false);
    }
  };

  return (
    <div className="max-w-[1600px] mx-auto space-y-6">
      {/* Header Section */}
      <div className="flex items-start justify-between animate-slide-in-left">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-white shadow-glow-primary animate-float">
            <BarChart3 className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-primary-light to-primary bg-clip-text text-transparent">
              Campaign Dashboard
            </h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              Manage and monitor SMS campaigns across your stores
            </p>
          </div>
        </div>
        <Button
          variant="primary"
          onClick={() => setShowPreviewModal(true)}
          disabled={!selectedStoreId}
          className="animate-scale-in"
        >
          <Rocket className="w-5 h-5" />
          <span>Start New Campaign</span>
        </Button>
      </div>

      {/* Store Selector */}
      <Card className="animate-slide-in-left">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
              <StoreIcon className="w-5 h-5 text-primary-light" />
            </div>
            <label className="text-dark-text-primary font-semibold whitespace-nowrap">
              Select Store:
            </label>
          </div>
          <div className="flex-1 w-full sm:max-w-md relative store-selector-dropdown">
            <button
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="w-full px-4 py-3 pl-12 pr-10 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary-light focus:outline-none transition-all duration-300 hover:border-primary/50 font-medium shadow-sm hover:shadow-md text-left flex items-center justify-between cursor-pointer"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                {selectedStoreId && (
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                    <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                  </div>
                )}
                <span className="truncate">
                  {selectedStore 
                    ? `${selectedStore.name} - ${selectedStore.location}`
                    : 'Choose a store...'}
                </span>
              </div>
              <ChevronDown 
                className={`w-4 h-4 text-dark-text-muted transition-transform duration-300 flex-shrink-0 ${
                  isDropdownOpen ? 'rotate-180' : ''
                }`} 
              />
            </button>
            
            {/* Custom Dropdown */}
            {isDropdownOpen && (
              <div className="absolute z-50 w-full mt-2 bg-dark-elevated border-2 border-dark-border rounded-lg shadow-xl max-h-64 overflow-y-auto animate-scale-in">
                {stores.length === 0 ? (
                  <div className="px-4 py-3 text-sm text-dark-text-muted text-center">
                    No stores available
                  </div>
                ) : (
                  stores.map((store) => (
                    <button
                      key={store.store_id}
                      type="button"
                      onClick={() => {
                        setSelectedStoreId(store.store_id);
                        setIsDropdownOpen(false);
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
                  ))
                )}
              </div>
            )}
          </div>
          {selectedStore && (
            <div className="hidden md:flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/20 rounded-lg flex-shrink-0">
              <span className="text-xs text-dark-text-muted">Active:</span>
              <span className="text-sm font-semibold text-primary-light">{selectedStore.name}</span>
            </div>
          )}
        </div>
      </Card>

      {selectedStoreId && selectedStore ? (
        <>
          {/* Daily Progress Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-slide-in-left">
            <KPICard
              icon={<MessageSquare className="w-7 h-7" />}
              title="SMS Sent Today"
              value={loading || !dailyStats ? '...' : `${dailyStats.sms_sent_today || 0} / ${selectedStore.daily_sms_quota}`}
              subtitle={loading || !dailyStats ? 'Loading...' : `${smsProgress.toFixed(1)}% of daily quota`}
              variant={loading || !dailyStats ? 'primary' : smsProgress >= 90 ? 'danger' : smsProgress >= 70 ? 'warning' : 'success'}
              loading={loading || !dailyStats}
            />
            <KPICard
              icon={<Phone className="w-7 h-7" />}
              title="Calls Made Today"
              value={loading || !dailyStats ? '...' : `${dailyStats.calls_made_today || 0} / ${selectedStore.daily_call_quota}`}
              subtitle={loading || !dailyStats ? 'Loading...' : `${callProgress.toFixed(1)}% of daily quota`}
              variant={loading || !dailyStats ? 'primary' : callProgress >= 90 ? 'danger' : callProgress >= 70 ? 'warning' : 'info'}
              loading={loading || !dailyStats}
            />
          </div>

          {/* Progress Bars */}
          <Card title="Daily Quota Progress" className="animate-scale-in">
            {loading || !dailyStats ? (
              <div className="text-center py-12 text-dark-text-secondary">
                <div className="animate-spin inline-block w-8 h-8 border-4 border-primary-light border-t-transparent rounded-full mb-4"></div>
                <p>Loading progress data...</p>
              </div>
            ) : (
              <div className="space-y-6 mt-6">
                {/* SMS Progress Bar */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-semibold text-dark-text-primary">
                      SMS Progress
                    </span>
                    <span className="text-sm text-dark-text-secondary">
                      {dailyStats.sms_sent_today || 0} / {selectedStore.daily_sms_quota}
                    </span>
                  </div>
                  <div className="w-full bg-dark-elevated rounded-full h-4 overflow-hidden border-2 border-dark-border">
                    <div
                      className={`h-full transition-all duration-500 ${
                        smsProgress >= 90
                          ? 'bg-gradient-to-r from-danger-light to-danger-dark'
                          : smsProgress >= 70
                          ? 'bg-gradient-to-r from-warning-light to-warning-dark'
                          : 'bg-gradient-to-r from-success-light to-success-dark'
                      }`}
                      style={{ width: `${Math.min(smsProgress, 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* Call Progress Bar */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-semibold text-dark-text-primary">
                      Call Progress
                    </span>
                    <span className="text-sm text-dark-text-secondary">
                      {dailyStats.calls_made_today || 0} / {selectedStore.daily_call_quota}
                    </span>
                  </div>
                  <div className="w-full bg-dark-elevated rounded-full h-4 overflow-hidden border-2 border-dark-border">
                    <div
                      className={`h-full transition-all duration-500 ${
                        callProgress >= 90
                          ? 'bg-gradient-to-r from-danger-light to-danger-dark'
                          : callProgress >= 70
                          ? 'bg-gradient-to-r from-warning-light to-warning-dark'
                          : 'bg-gradient-to-r from-info-light to-info-dark'
                      }`}
                      style={{ width: `${Math.min(callProgress, 100)}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* All Campaigns Section */}
          <Card
            title="SMS Campaigns"
            subtitle={`${allCampaigns.length} campaign(s) for this store`}
            className="animate-scale-in stagger-1"
          >
            {loading ? (
              <div className="text-center py-12 text-dark-text-secondary">
                <div className="animate-spin inline-block w-12 h-12 border-4 border-primary-light border-t-transparent rounded-full mb-4"></div>
                <p>Loading campaigns...</p>
              </div>
            ) : allCampaigns.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4 animate-bounce">
                  <Activity className="w-10 h-10 text-dark-text-muted" />
                </div>
                <h3 className="text-xl font-bold text-dark-text-primary mb-2">
                  No Campaigns Yet
                </h3>
                <p className="text-sm text-dark-text-muted mb-6">
                  Start a new campaign to begin reaching out to your leads
                </p>
                <Button variant="primary" onClick={() => setShowPreviewModal(true)}>
                  <Rocket className="w-5 h-5" />
                  <span>Start Your First Campaign</span>
                </Button>
              </div>
            ) : (
              <div className="space-y-4 mt-6">
                {allCampaigns.map((campaign, index) => (
                  <div
                    key={campaign.campaign_id}
                    className="p-4 bg-dark-elevated border-2 border-dark-border rounded-lg hover:border-primary-light transition-all duration-300 hover:scale-102 card-glow animate-slide-in-left"
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                          <MessageSquare className="w-5 h-5 text-primary-light" />
                        </div>
                        <div>
                          <h4 className="text-base font-bold text-dark-text-primary">
                            Campaign #{campaign.campaign_id}
                          </h4>
                          <p className="text-xs text-dark-text-secondary">
                            Started {new Date(campaign.created_at || '').toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <Badge
                        variant={
                          campaign.status === 'completed'
                            ? 'success'
                            : campaign.status === 'active'
                            ? 'info'
                            : campaign.status === 'pending'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {campaign.status.toUpperCase()}
                      </Badge>
                    </div>

                    {/* SMS Results Summary - 4 columns: Sent, Target, Pending, Failed */}
                    <div className="grid grid-cols-4 gap-2 mb-4">
                      <div className="text-center p-2 bg-success/10 rounded border border-success/30">
                        <div className="text-lg font-bold text-success-light">{campaign.actual_sent}</div>
                        <div className="text-xs text-dark-text-muted">Sent</div>
                      </div>
                      <div className="text-center p-2 bg-dark-surface rounded border border-dark-border">
                        <div className="text-lg font-bold text-dark-text-primary">{campaign.target_count}</div>
                        <div className="text-xs text-dark-text-muted">Target</div>
                      </div>
                      <div className="text-center p-2 bg-warning/10 rounded border border-warning/30">
                        <div className="text-lg font-bold text-warning-light">
                          {campaign.pending_batches * 25}
                        </div>
                        <div className="text-xs text-dark-text-muted">Pending</div>
                      </div>
                      <div className="text-center p-2 bg-danger/10 rounded border border-danger/30">
                        <div className="text-lg font-bold text-danger-light">
                          {Math.max(0, campaign.target_count - campaign.actual_sent - (campaign.pending_batches * 25))}
                        </div>
                        <div className="text-xs text-dark-text-muted">Failed</div>
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div className="mb-3">
                      <div className="w-full bg-dark-surface rounded-full h-3 overflow-hidden border border-dark-border">
                        <div
                          className={`h-full transition-all duration-500 ${
                            campaign.progress_percentage >= 90 ? 'bg-gradient-to-r from-success-light to-success' : 
                            campaign.progress_percentage >= 70 ? 'bg-gradient-to-r from-warning-light to-warning' : 
                            campaign.progress_percentage >= 50 ? 'bg-gradient-to-r from-primary-light to-primary' :
                            'bg-gradient-to-r from-danger-light to-danger'
                          }`}
                          style={{ width: `${campaign.progress_percentage}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between mt-1 text-xs">
                        <span className="text-dark-text-muted">
                          {campaign.completed_batches}/{campaign.batch_count} batches done
                        </span>
                        <span className={`font-bold ${
                          campaign.progress_percentage >= 90 ? 'text-success-light' : 
                          campaign.progress_percentage >= 70 ? 'text-warning-light' : 'text-danger-light'
                        }`}>{campaign.progress_percentage}% success</span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-between items-center">
                      <div className="flex gap-2">
                        <Button 
                          variant="secondary" 
                          size="sm"
                          onClick={() => viewCampaignDetails(campaign.campaign_id)}
                        >
                          <BarChart3 className="w-4 h-4" />
                          Details
                        </Button>
                        {campaign.status !== 'completed' && (
                          campaign.status === 'paused' ? (
                            <Button 
                              variant="success" 
                              size="sm"
                              onClick={() => handleResumeCampaign(campaign.campaign_id)}
                            >
                              <Play className="w-4 h-4" />
                              Resume
                            </Button>
                          ) : (
                            <Button 
                              variant="warning" 
                              size="sm"
                              onClick={() => handlePauseCampaign(campaign.campaign_id)}
                            >
                              <Pause className="w-4 h-4" />
                              Pause
                            </Button>
                          )
                        )}
                        <Button 
                          variant="danger" 
                          size="sm"
                          onClick={() => handleDeleteCampaign(campaign.campaign_id)}
                          title="Delete campaign"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Phone Number Health Section */}
          <Card
            title="Phone Number Health"
            subtitle={`${phoneNumbers.length} number(s) assigned to this store`}
            className="animate-scale-in stagger-2"
          >
            {loading ? (
              <div className="text-center py-8 text-dark-text-secondary">
                <div className="animate-spin inline-block w-10 h-10 border-4 border-primary-light border-t-transparent rounded-full"></div>
              </div>
            ) : phoneNumbers.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-16 h-16 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4 animate-bounce">
                  <PhoneOff className="w-8 h-8 text-dark-text-muted" />
                </div>
                <p className="text-dark-text-muted font-medium">
                  No phone numbers assigned to this store
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
                {phoneNumbers.map((phone, index) => (
                  <div
                    key={phone.phone_number_id}
                    className={`p-4 rounded-lg border-2 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-right ${
                      phone.health_status === 'healthy'
                        ? 'bg-success/5 border-success/30 hover:border-success/50'
                        : phone.health_status === 'warning'
                        ? 'bg-warning/5 border-warning/30 hover:border-warning/50'
                        : 'bg-danger/5 border-danger/30 hover:border-danger/50'
                    }`}
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="font-mono text-sm text-dark-text-primary font-semibold">
                          {phone.phone_number}
                        </p>
                        <Badge
                          variant={
                            phone.health_status === 'healthy'
                              ? 'success'
                              : phone.health_status === 'warning'
                              ? 'warning'
                              : 'error'
                          }
                        >
                          {phone.health_status.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center">
                        {phone.health_status === 'healthy' ? (
                          <CheckCircle2 className="w-6 h-6 text-success-light" />
                        ) : phone.health_status === 'warning' ? (
                          <AlertCircle className="w-6 h-6 text-warning-light" />
                        ) : (
                          <XCircle className="w-6 h-6 text-danger-light" />
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs py-1.5 px-2 bg-dark-surface rounded">
                        <span className="text-dark-text-muted">Hourly SMS</span>
                        <span className="text-dark-text-primary font-bold">
                          {phone.hourly_sms_count} <span className="text-dark-text-muted font-normal">/ 25</span>
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs py-1.5 px-2 bg-dark-surface rounded">
                        <span className="text-dark-text-muted">Daily SMS</span>
                        <span className="text-dark-text-primary font-bold">
                          {phone.daily_sms_count} <span className="text-dark-text-muted font-normal">/ 50</span>
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs py-1.5 px-2 bg-dark-surface rounded">
                        <span className="text-dark-text-muted">Daily Calls</span>
                        <span className="text-dark-text-primary font-bold">
                          {phone.daily_call_count} <span className="text-dark-text-muted font-normal">/ 30</span>
                        </span>
                      </div>

                      {/* Capacity Bar */}
                      <div className="pt-1">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-dark-text-muted">Capacity</span>
                          <span className="text-dark-text-primary font-semibold">
                            {phone.sms_capacity_percentage}%
                          </span>
                        </div>
                        <div className="w-full bg-dark-surface rounded-full h-2 overflow-hidden border border-dark-border">
                          <div
                            className={`h-full transition-all duration-500 ${
                              phone.health_status === 'healthy'
                                ? 'bg-gradient-to-r from-success to-success-light'
                                : phone.health_status === 'warning'
                                ? 'bg-gradient-to-r from-warning to-warning-light'
                                : 'bg-gradient-to-r from-danger to-danger-light'
                            }`}
                            style={{ width: `${phone.sms_capacity_percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      ) : (
        <Card className="animate-scale-in">
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4 animate-bounce">
              <StoreIcon className="w-10 h-10 text-dark-text-muted" />
            </div>
            <h3 className="text-xl font-bold text-dark-text-primary mb-2">
              Select a Store
            </h3>
            <p className="text-sm text-dark-text-muted">
              Choose a store from the dropdown above to view campaign dashboard
            </p>
          </div>
        </Card>
      )}

      {/* Campaign Preview Modal - Milestone 14 */}
      {showPreviewModal && selectedStore && (
        <CampaignPreviewModal
          storeId={selectedStore.store_id}
          storeName={selectedStore.name}
          onClose={() => setShowPreviewModal(false)}
          onSuccess={(campaign: StartCampaignResponse) => {
            setShowPreviewModal(false);
            // Refresh data silently (no loading state)
            loadStoreData(true);
            // Show success message
            alert(`✅ Campaign #${campaign.campaign_id} started successfully! ${campaign.batch_count} batches scheduled.`);
          }}
        />
      )}

      {/* Campaign Details Modal - Redesigned for clarity */}
      {showDetailsModal && (
        <div 
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 animate-fade-in p-4"
          onClick={(e) => {
            // Close modal when clicking on backdrop (outside the modal content)
            if (e.target === e.currentTarget) {
              setShowDetailsModal(false);
              setSelectedCampaignDetails(null);
              setExpandedBatchId(null);
              setBatchLeads(null);
            }
          }}
        >
          <div className="bg-dark-surface border border-dark-border rounded-2xl w-full max-w-5xl max-h-[95vh] overflow-hidden shadow-2xl animate-scale-in flex flex-col">
            {/* Modal Header - Clean and informative */}
            <div className="px-6 py-4 border-b border-dark-border bg-gradient-to-r from-dark-elevated to-dark-surface">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-0.5 bg-primary/20 text-primary-light text-xs font-medium rounded">
                      Campaign #{selectedCampaignDetails?.campaign?.campaign_id}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                      selectedCampaignDetails?.campaign?.status === 'completed' ? 'bg-success/20 text-success-light' :
                      selectedCampaignDetails?.campaign?.status === 'active' ? 'bg-info/20 text-info-light' :
                      'bg-warning/20 text-warning-light'
                    }`}>
                      {selectedCampaignDetails?.campaign?.status?.toUpperCase()}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-dark-text-primary">
                    SMS Campaign Results
                  </h2>
                  <p className="text-sm text-dark-text-muted mt-1">
                    Store: {selectedCampaignDetails?.campaign?.store_name} • Started: {selectedCampaignDetails?.campaign?.started_at ? new Date(selectedCampaignDetails.campaign.started_at).toLocaleString() : 'N/A'}
                  </p>
                </div>
                <button
                  onClick={() => { setShowDetailsModal(false); setSelectedCampaignDetails(null); setExpandedBatchId(null); setBatchLeads(null); }}
                  className="w-8 h-8 rounded-full bg-dark-surface border border-dark-border flex items-center justify-center hover:bg-danger/20 hover:border-danger/50 transition-all"
                >
                  <XCircle className="w-5 h-5 text-dark-text-muted hover:text-danger-light" />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="overflow-y-auto flex-1">
              {loadingDetails ? (
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="animate-spin w-12 h-12 border-4 border-primary-light border-t-transparent rounded-full mb-4"></div>
                  <p className="text-dark-text-muted">Loading campaign details...</p>
                </div>
              ) : selectedCampaignDetails?.campaign ? (
                <div className="p-6 space-y-6">
                  {/* Campaign Summary Cards - Large and clear */}
                  <div>
                    <h3 className="text-xs font-semibold text-dark-text-muted uppercase tracking-wider mb-3">
                      📊 Campaign Summary
                    </h3>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="bg-gradient-to-br from-success/20 to-success/5 rounded-xl p-4 border border-success/30">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle className="w-5 h-5 text-success-light" />
                          <span className="text-xs font-medium text-success-light">Sent</span>
                        </div>
                        <div className="text-3xl font-bold text-success-light">
                          {selectedCampaignDetails.campaign.actual_sent}
                        </div>
                        <div className="text-xs text-dark-text-muted mt-1">
                          {Math.round((selectedCampaignDetails.campaign.actual_sent / selectedCampaignDetails.campaign.target_count) * 100)}% success rate
                        </div>
                      </div>
                      
                      <div className="bg-gradient-to-br from-dark-elevated to-dark-surface rounded-xl p-4 border border-dark-border">
                        <div className="flex items-center gap-2 mb-2">
                          <Users className="w-5 h-5 text-dark-text-secondary" />
                          <span className="text-xs font-medium text-dark-text-secondary">Target</span>
                        </div>
                        <div className="text-3xl font-bold text-dark-text-primary">
                          {selectedCampaignDetails.campaign.target_count}
                        </div>
                        <div className="text-xs text-dark-text-muted mt-1">
                          total leads
                        </div>
                      </div>
                      
                      <div className="bg-gradient-to-br from-warning/20 to-warning/5 rounded-xl p-4 border border-warning/30">
                        <div className="flex items-center gap-2 mb-2">
                          <Clock className="w-5 h-5 text-warning-light" />
                          <span className="text-xs font-medium text-warning-light">Pending</span>
                        </div>
                        <div className="text-3xl font-bold text-warning-light">
                          {selectedCampaignDetails.batches?.reduce((sum: number, b: any) => 
                            sum + (b.status === 'pending' ? (b.target_count || 25) : 0), 0) || 0}
                        </div>
                        <div className="text-xs text-dark-text-muted mt-1">
                          awaiting send
                        </div>
                      </div>
                      
                      <div className="bg-gradient-to-br from-danger/20 to-danger/5 rounded-xl p-4 border border-danger/30">
                        <div className="flex items-center gap-2 mb-2">
                          <AlertCircle className="w-5 h-5 text-danger-light" />
                          <span className="text-xs font-medium text-danger-light">Failed</span>
                        </div>
                        <div className="text-3xl font-bold text-danger-light">
                          {selectedCampaignDetails.batches?.reduce((sum: number, b: any) => 
                            sum + (b.status !== 'pending' ? ((b.target_count || 25) - (b.actual_sent || 0)) : 0), 0) || 0}
                        </div>
                        <div className="text-xs text-dark-text-muted mt-1">
                          could not send
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Batch Breakdown Section */}
                  <div>
                    <h3 className="text-xs font-semibold text-dark-text-muted uppercase tracking-wider mb-3">
                      📦 Batch Details ({selectedCampaignDetails.batches?.length || 0} batches)
                    </h3>
                    <div className="space-y-3">
                      {selectedCampaignDetails.batches?.map((batch: any, index: number) => {
                        const failedCount = (batch.target_count || 25) - (batch.actual_sent || 0);
                        const isExpanded = expandedBatchId === batch.batch_id;
                        const successRate = batch.target_count > 0 ? Math.round((batch.actual_sent || 0) / batch.target_count * 100) : 0;
                        
                        return (
                          <div 
                            key={batch.batch_id} 
                            className={`rounded-xl border overflow-hidden transition-all ${
                              batch.status === 'completed' ? 'border-success/30 bg-success/5' :
                              batch.status === 'failed' ? 'border-danger/30 bg-danger/5' :
                              batch.status === 'running' || batch.status === 'executing' ? 'border-info/30 bg-info/5' :
                              'border-dark-border bg-dark-elevated'
                            }`}
                          >
                            {/* Batch Header */}
                            <div className="p-4">
                              <div className="flex justify-between items-center mb-3">
                                <div className="flex items-center gap-3">
                                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                                    batch.status === 'completed' ? 'bg-success/20 text-success-light' :
                                    batch.status === 'failed' ? 'bg-danger/20 text-danger-light' :
                                    batch.status === 'running' || batch.status === 'executing' ? 'bg-info/20 text-info-light' :
                                    'bg-dark-surface text-dark-text-muted'
                                  }`}>
                                    {index + 1}
                                  </div>
                                  <div>
                                    <div className="font-semibold text-dark-text-primary">
                                      Batch #{batch.batch_number || index + 1}
                                    </div>
                                    <div className="text-xs text-dark-text-muted">
                                      {batch.status === 'completed' && batch.completed_at ? 
                                        `Completed ${new Date(batch.completed_at).toLocaleTimeString()}` :
                                        batch.status === 'pending' ? 
                                        `Scheduled for ${batch.scheduled_at ? new Date(batch.scheduled_at).toLocaleTimeString() : 'later'}` :
                                        batch.status.charAt(0).toUpperCase() + batch.status.slice(1)
                                      }
                                    </div>
                                  </div>
                                </div>
                                <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                                  batch.status === 'completed' ? 'bg-success/20 text-success-light' :
                                  batch.status === 'failed' ? 'bg-danger/20 text-danger-light' :
                                  batch.status === 'running' || batch.status === 'executing' ? 'bg-info/20 text-info-light' :
                                  'bg-warning/20 text-warning-light'
                                }`}>
                                  {batch.status === 'executing' ? 'RUNNING' : batch.status.toUpperCase()}
                                </div>
                              </div>

                              {/* Progress Bar */}
                              {batch.status !== 'pending' && (
                                <div className="mb-3">
                                  <div className="flex justify-between text-xs mb-1">
                                    <span className="text-dark-text-muted">Progress</span>
                                    <span className={successRate >= 80 ? 'text-success-light' : successRate >= 50 ? 'text-warning-light' : 'text-danger-light'}>
                                      {successRate}% success
                                    </span>
                                  </div>
                                  <div className="h-2 bg-dark-surface rounded-full overflow-hidden">
                                    <div 
                                      className={`h-full rounded-full transition-all ${
                                        successRate >= 80 ? 'bg-success' : successRate >= 50 ? 'bg-warning' : 'bg-danger'
                                      }`}
                                      style={{ width: `${successRate}%` }}
                                    />
                                  </div>
                                </div>
                              )}

                              {/* Stats Row */}
                              <div className="grid grid-cols-3 gap-3">
                                <div className="text-center p-2 bg-dark-surface/50 rounded-lg">
                                  <div className="text-lg font-bold text-success-light">{batch.actual_sent || 0}</div>
                                  <div className="text-[10px] text-dark-text-muted uppercase">Sent</div>
                                </div>
                                <div className="text-center p-2 bg-dark-surface/50 rounded-lg">
                                  <div className="text-lg font-bold text-dark-text-primary">{batch.target_count || 25}</div>
                                  <div className="text-[10px] text-dark-text-muted uppercase">Target</div>
                                </div>
                                <div className="text-center p-2 bg-dark-surface/50 rounded-lg">
                                  <div className={`text-lg font-bold ${failedCount > 0 ? 'text-danger-light' : 'text-success-light'}`}>
                                    {failedCount}
                                  </div>
                                  <div className="text-[10px] text-dark-text-muted uppercase">Failed</div>
                                </div>
                              </div>

                              {/* View Failed Leads Button */}
                              {failedCount > 0 && batch.status !== 'pending' && (
                                <button
                                  onClick={() => loadBatchLeads(batch.batch_id)}
                                  className={`mt-3 w-full py-2.5 px-4 text-sm font-medium rounded-lg transition-all flex items-center justify-center gap-2 ${
                                    isExpanded 
                                      ? 'bg-danger/20 border border-danger/40 text-danger-light' 
                                      : 'bg-dark-surface border border-dark-border text-dark-text-secondary hover:border-danger/40 hover:text-danger-light'
                                  }`}
                                >
                                  {loadingBatchLeads && isExpanded ? (
                                    <><div className="animate-spin w-4 h-4 border-2 border-danger-light border-t-transparent rounded-full"></div>Loading failure details...</>
                                  ) : isExpanded ? (
                                    <><ChevronUp className="w-4 h-4" />Hide {failedCount} Failed Lead{failedCount !== 1 ? 's' : ''}</>
                                  ) : (
                                    <><ChevronDown className="w-4 h-4" />Show {failedCount} Failed Lead{failedCount !== 1 ? 's' : ''} with Reasons</>
                                  )}
                                </button>
                              )}
                            </div>

                            {/* Expanded Failed Leads Section */}
                            {isExpanded && batchLeads && (
                              <div className="border-t border-dark-border bg-dark-surface/50 p-4">
                                <div className="flex items-center gap-2 mb-3">
                                  <AlertCircle className="w-4 h-4 text-danger-light" />
                                  <span className="text-sm font-semibold text-dark-text-primary">
                                    Failed Leads ({batchLeads.failed_count || 0})
                                  </span>
                                </div>
                                  
                                {batchLeads.failed_leads?.length > 0 ? (
                                  <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {batchLeads.failed_leads.map((lead: any) => (
                                      <div 
                                        key={lead.lead_id}
                                        className="p-3 bg-danger/5 border border-danger/20 rounded-lg"
                                      >
                                        <div className="flex justify-between items-start mb-2">
                                          <div>
                                            <span className="font-medium text-dark-text-primary">
                                              {lead.lead_name || 'Unknown'}
                                            </span>
                                            <span className="text-dark-text-muted ml-2 text-sm">
                                              {lead.phone_number}
                                            </span>
                                          </div>
                                          {lead.error_code && (
                                            <span className="px-2 py-1 bg-danger/20 text-danger-light rounded text-xs font-mono">
                                              Error {lead.error_code}
                                            </span>
                                          )}
                                        </div>
                                        <div className="flex items-start gap-2 text-sm">
                                          <AlertCircle className="w-4 h-4 text-danger-light flex-shrink-0 mt-0.5" />
                                          <span className="text-danger-light">
                                            {lead.error_message || 'Unknown error occurred'}
                                          </span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <div className="text-center py-4 text-dark-text-muted">
                                    No detailed failure information available for this batch.
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-dark-text-muted">
                  <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
                  <p>No campaign details available</p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-dark-border bg-dark-elevated flex justify-end">
              <Button
                variant="secondary"
                onClick={() => { setShowDetailsModal(false); setSelectedCampaignDetails(null); setExpandedBatchId(null); setBatchLeads(null); }}
                className="px-6"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CampaignDashboardPage;
