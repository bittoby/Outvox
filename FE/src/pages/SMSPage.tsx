// SMS Management Page - Clear, User-Friendly & Awesome

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  MessageSquare, 
  Camera, 
  Search, 
  RefreshCw, 
  Eye, 
  CheckCircle, 
  Clock, 
  Filter,
  Phone,
  MapPin,
  User,
  Image as ImageIcon,
  ArrowUp,
  ArrowDown,
  Star,
  AlertCircle,
  X,
  Trash2
} from 'lucide-react';
import Card from '../components/Card/Card';
import Button from '../components/Button/Button';
import Badge from '../components/Badge/Badge';
import { getAllSMSConversations, getAllPhotoSubmissions, updatePhotoStatus, SMSConversation, PhotoSubmission } from '../services/api';
import { clearConversations, clearPhotoSubmissions, deleteSMSConversation, deletePhotoSubmission } from '../services/api/sms';
import { useWebSocket, EventType } from '../hooks/useWebSocket';
import toast, { Toaster } from 'react-hot-toast';

const SMSPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'conversations' | 'photos'>('conversations');
  const [conversations, setConversations] = useState<SMSConversation[]>([]);
  const [photos, setPhotos] = useState<PhotoSubmission[]>([]);
  const [totalConversations, setTotalConversations] = useState(0);
  const [totalPhotos, setTotalPhotos] = useState(0);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [directionFilter, setDirectionFilter] = useState<'all' | 'inbound' | 'outbound'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'reviewed' | 'appraised'>('all');
  const [selectedPhoto, setSelectedPhoto] = useState<PhotoSubmission | null>(null);
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest');
  const [showFilters, setShowFilters] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Load data functions
  const loadConversations = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getAllSMSConversations(100, 0, directionFilter === 'all' ? undefined : directionFilter);
      setConversations(response.conversations || []);
      setTotalConversations(response.total_count || 0);
    } catch (error) {
      console.error('Error loading conversations:', error);
      setConversations([]);
      setTotalConversations(0);
      toast.error('Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, [directionFilter]);

  const loadPhotos = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getAllPhotoSubmissions(100, 0, statusFilter === 'all' ? undefined : statusFilter);
      setPhotos(response.photos);
      setTotalPhotos(response.total_count || response.photos.length);
    } catch (error) {
      console.error('Error loading photos:', error);
      toast.error('Failed to load photos');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  // Refresh function
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      if (activeTab === 'conversations') {
        await loadConversations();
      } else {
        await loadPhotos();
      }
      setLastUpdate(new Date());
      toast.success('Data refreshed successfully');
    } catch (error) {
      toast.error('Failed to refresh data');
    } finally {
      setRefreshing(false);
    }
  }, [activeTab, loadConversations, loadPhotos]);

  // Load both conversations and photos on initial mount
  useEffect(() => {
    loadConversations();
    loadPhotos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reload conversations when direction filter changes
  useEffect(() => {
    loadConversations();
  }, [directionFilter, loadConversations]);

  // Reload photos when status filter changes
  useEffect(() => {
    loadPhotos();
  }, [statusFilter, loadPhotos]);

  // Reload current tab data when tab changes
  useEffect(() => {
    if (activeTab === 'conversations') {
      loadConversations();
    } else {
      loadPhotos();
    }
  }, [activeTab, loadConversations, loadPhotos]);

  // WebSocket for real-time updates
  const { subscribe, on } = useWebSocket({ autoConnect: true });

  // Register event handlers immediately (don't wait for connected state)
  // The WebSocket client will queue messages if not connected yet
  useEffect(() => {
    // Subscribe to SMS and photo events
    subscribe([
      EventType.SMS_RECEIVED,
      EventType.SMS_SENT,
      EventType.PHOTO_SUBMITTED,
      EventType.PHOTO_UPDATED,
    ]);

    // Handle SMS received
    const unsubscribeSMS = on(EventType.SMS_RECEIVED, () => {
      loadConversations();
      setLastUpdate(new Date());
    });

    // Handle SMS sent
    const unsubscribeSMSSent = on(EventType.SMS_SENT, () => {
      loadConversations();
      setLastUpdate(new Date());
    });

    // Handle photo submitted
    const unsubscribePhoto = on(EventType.PHOTO_SUBMITTED, () => {
      loadPhotos();
      setLastUpdate(new Date());
    });

    // Handle photo updated
    const unsubscribePhotoUpdate = on(EventType.PHOTO_UPDATED, () => {
      loadPhotos();
      setLastUpdate(new Date());
    });

    return () => {
      unsubscribeSMS();
      unsubscribeSMSSent();
      unsubscribePhoto();
      unsubscribePhotoUpdate();
    };
  }, [subscribe, on, loadConversations, loadPhotos]);

  // No polling - only real-time updates via WebSocket

  // Photo status update
  const handlePhotoStatusUpdate = async (photoId: number, status: 'pending' | 'reviewed' | 'appraised') => {
    try {
      await updatePhotoStatus(photoId, status, 'Admin');
      await loadPhotos();
      toast.success(`Photo marked as ${status}`);
    } catch (error) {
      console.error('Error updating photo status:', error);
      toast.error('Failed to update photo status');
    }
  };

  // Delete SMS conversation
  const handleDeleteConversation = async (leadId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this SMS conversation? This action cannot be undone.')) {
      return;
    }
    try {
      await deleteSMSConversation(leadId);
      await loadConversations();
      toast.success('SMS conversation deleted successfully');
    } catch (error) {
      console.error('Error deleting conversation:', error);
      toast.error('Failed to delete conversation');
    }
  };

  // Delete photo submission
  const handleDeletePhoto = async (photoId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this photo submission? This action cannot be undone.')) {
      return;
    }
    try {
      await deletePhotoSubmission(photoId);
      await loadPhotos();
      toast.success('Photo deleted successfully');
    } catch (error) {
      console.error('Error deleting photo:', error);
      toast.error('Failed to delete photo');
    }
  };

  // Delete all conversations
  const handleDeleteAllConversations = async () => {
    if (!window.confirm(
      `⚠️ Are you sure you want to delete ALL SMS conversations?\n\n` +
      `This will permanently delete ${totalConversations} conversation(s).\n\n` +
      `This action cannot be undone!`
    )) {
      return;
    }
    try {
      await clearConversations();
      await loadConversations();
      toast.success('All conversations deleted successfully');
    } catch (error) {
      console.error('Error deleting all conversations:', error);
      toast.error('Failed to delete all conversations');
    }
  };

  // Delete all photos
  const handleDeleteAllPhotos = async () => {
    if (!window.confirm(
      `⚠️ Are you sure you want to delete ALL photo submissions?\n\n` +
      `This will permanently delete ${totalPhotos} photo(s).\n\n` +
      `This action cannot be undone!`
    )) {
      return;
    }
    try {
      await clearPhotoSubmissions();
      await loadPhotos();
      toast.success('All photos deleted successfully');
    } catch (error) {
      console.error('Error deleting all photos:', error);
      toast.error('Failed to delete all photos');
    }
  };

  // Filter and sort data
  const filteredConversations = (conversations || [])
    .filter(conv => {
      if (!conv) return false;
      
      // Apply direction filter
      if (directionFilter !== 'all' && conv.direction !== directionFilter) {
        return false;
      }
      
      // Apply search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const messageMatch = conv.message_content 
          ? conv.message_content.toLowerCase().includes(searchLower)
          : false;
        const phoneMatch = conv.phone_number 
          ? conv.phone_number.includes(searchTerm)
          : false;
        const nameMatch = conv.lead_name 
          ? conv.lead_name.toLowerCase().includes(searchLower)
          : false;
        const cityMatch = conv.city 
          ? conv.city.toLowerCase().includes(searchLower)
          : false;
        const stateMatch = conv.state 
          ? conv.state.toLowerCase().includes(searchLower)
          : false;
        return messageMatch || phoneMatch || nameMatch || cityMatch || stateMatch;
      }
      return true;
    })
    .sort((a, b) => {
      if (!a || !b) return 0;
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return sortBy === 'newest' ? dateB - dateA : dateA - dateB;
    });

  const filteredPhotos = (photos || [])
    .filter(photo => {
      if (!photo) return false;
      const searchLower = searchTerm.toLowerCase();
      const phoneMatch = photo.phone_number 
        ? photo.phone_number.includes(searchTerm)
        : false;
      const nameMatch = photo.lead_name 
        ? photo.lead_name.toLowerCase().includes(searchLower)
        : false;
      return phoneMatch || nameMatch;
    })
    .sort((a, b) => {
      if (!a || !b) return 0;
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return sortBy === 'newest' ? dateB - dateA : dateA - dateB;
    });

  // Calculate stats
  const inboundCount = conversations.filter(c => c.direction === 'inbound').length;
  const pendingPhotos = photos.filter(p => p.status === 'pending').length;

  // Utility functions
  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      // Show full date and time: "MM/DD/YYYY, HH:MM:SS AM/PM"
      return date.toLocaleString('en-US', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    } catch (error) {
      return 'Invalid Date';
    }
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'pending':
        return { 
          color: 'warning', 
          icon: Clock, 
          label: 'Pending Review' 
        };
      case 'reviewed':
        return { 
          color: 'info', 
          icon: CheckCircle, 
          label: 'Reviewed' 
        };
      case 'appraised':
        return { 
          color: 'success', 
          icon: Star, 
          label: 'Appraised' 
        };
      default:
        return { 
          color: 'neutral', 
          icon: AlertCircle, 
          label: 'Unknown' 
        };
    }
  };

  const getDirectionConfig = (direction: string) => {
    return direction === 'inbound' 
      ? { 
          color: 'success', 
          icon: ArrowDown, 
          label: 'Incoming' 
        }
      : { 
          color: 'primary', 
          icon: ArrowUp, 
          label: 'Outgoing' 
        };
  };

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 px-4">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex items-start justify-between animate-slide-in-left">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-warning to-warning-dark flex items-center justify-center text-white shadow-glow-warning animate-float">
            <MessageSquare className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-warning-light to-warning bg-clip-text text-transparent">
              SMS Management
            </h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              Manage customer conversations and photo submissions
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            onClick={handleRefresh}
            disabled={refreshing}
            variant="secondary"
            className="animate-scale-in"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          <Button
            onClick={() => setShowFilters(!showFilters)}
            variant={showFilters ? "primary" : "secondary"}
            className="animate-scale-in"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-dark-surface border-2 border-dark-border hover:border-primary/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-primary-light" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Total Conversations</p>
              <p className="text-2xl font-bold text-dark-text-primary">{totalConversations}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-surface border-2 border-dark-border hover:border-success/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <ArrowDown className="w-5 h-5 text-success-light" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Inbound Messages</p>
              <p className="text-2xl font-bold text-dark-text-primary">{inboundCount}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-surface border-2 border-dark-border hover:border-info/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
              <Camera className="w-5 h-5 text-info-light" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Total Photos</p>
              <p className="text-2xl font-bold text-dark-text-primary">{totalPhotos}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-surface border-2 border-dark-border hover:border-warning/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-warning-light" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Pending Photos</p>
              <p className="text-2xl font-bold text-dark-text-primary">{pendingPhotos}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-dark-surface rounded-xl p-1 border-2 border-dark-border shadow-modern animate-slide-in-left">
        <button
          onClick={() => setActiveTab('conversations')}
          className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-lg font-semibold transition-all duration-300 ${
            activeTab === 'conversations'
              ? 'bg-gradient-to-r from-primary to-primary-dark text-white shadow-glow-primary'
              : 'text-dark-text-secondary hover:text-dark-text-primary hover:bg-dark-elevated'
          }`}
        >
          <MessageSquare className="w-5 h-5" />
          <span>Conversations</span>
          <Badge variant={activeTab === 'conversations' ? 'neutral' : 'primary'} size="sm">
            {totalConversations}
          </Badge>
        </button>
        <button
          onClick={() => setActiveTab('photos')}
          className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 rounded-lg font-semibold transition-all duration-300 ${
            activeTab === 'photos'
              ? 'bg-gradient-to-r from-primary to-primary-dark text-white shadow-glow-primary'
              : 'text-dark-text-secondary hover:text-dark-text-primary hover:bg-dark-elevated'
          }`}
        >
          <Camera className="w-5 h-5" />
          <span>Photos</span>
          <Badge variant={activeTab === 'photos' ? 'neutral' : 'primary'} size="sm">
            {totalPhotos}
          </Badge>
        </button>
      </div>

      {/* Filters and Search */}
      <Card className="animate-slide-in-left">
        <div className="space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-dark-text-muted w-5 h-5" />
            <input
              type="text"
              placeholder={activeTab === 'conversations' 
                ? "Search by phone, name, or message content..." 
                : "Search by phone or name..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-dark-elevated border-2 border-dark-border rounded-xl text-dark-text-primary placeholder-dark-text-muted focus:ring-2 focus:ring-primary focus:border-primary transition-all outline-none"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-4 top-1/2 transform -translate-y-1/2 text-dark-text-muted hover:text-dark-text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          
          {/* Advanced Filters */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-dark-border animate-fade-in-down">
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  {activeTab === 'conversations' ? 'Message Direction' : 'Photo Status'}
                </label>
                <select
                  value={activeTab === 'conversations' ? directionFilter : statusFilter}
                  onChange={(e) => {
                    if (activeTab === 'conversations') {
                      setDirectionFilter(e.target.value as any);
                    } else {
                      setStatusFilter(e.target.value as any);
                    }
                  }}
                  className="w-full px-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:ring-2 focus:ring-primary focus:border-primary transition-all outline-none"
                >
                  {activeTab === 'conversations' ? (
                    <>
                      <option value="all">All Messages</option>
                      <option value="inbound">Inbound Only</option>
                      <option value="outbound">Outbound Only</option>
                    </>
                  ) : (
                    <>
                      <option value="all">All Status</option>
                      <option value="pending">Pending</option>
                      <option value="reviewed">Reviewed</option>
                      <option value="appraised">Appraised</option>
                    </>
                  )}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">Sort By</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="w-full px-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:ring-2 focus:ring-primary focus:border-primary transition-all outline-none"
                >
                  <option value="newest">Newest First</option>
                  <option value="oldest">Oldest First</option>
                </select>
              </div>
              
              <div className="flex items-end">
                <Button
                  onClick={() => {
                    setSearchTerm('');
                    setDirectionFilter('all');
                    setStatusFilter('all');
                    setSortBy('newest');
                  }}
                  variant="secondary"
                  className="w-full"
                >
                  Clear Filters
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Content */}
      {activeTab === 'conversations' ? (
        <Card 
          title="SMS Conversations" 
          subtitle={`${filteredConversations.length} message${filteredConversations.length !== 1 ? 's' : ''} found • Real-time updates via WebSocket`}
          action={
            <div className="flex items-center gap-3">
              {totalConversations > 0 && (
                <Button
                  onClick={handleDeleteAllConversations}
                  variant="danger"
                  size="sm"
                  className="animate-scale-in"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete All
                </Button>
              )}
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                <span className="text-xs text-dark-text-muted">
                  Updated {lastUpdate.toLocaleTimeString()}
                </span>
              </div>
            </div>
          }
          className="animate-scale-in"
        >
          {loading ? (
            <div className="space-y-4 py-8">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-24 bg-dark-elevated border border-dark-border rounded-lg animate-pulse"></div>
              ))}
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4">
                <MessageSquare className="w-10 h-10 text-dark-text-muted" />
              </div>
              <h3 className="text-lg font-bold text-dark-text-primary mb-2">No conversations found</h3>
              <p className="text-sm text-dark-text-muted mb-6 text-center max-w-md">
                {searchTerm || directionFilter !== 'all' 
                  ? "No SMS conversations match your current filters. Try adjusting your search or filters."
                  : "No SMS conversations yet. Conversations will appear here when customers send or receive messages."}
              </p>
              {(searchTerm || directionFilter !== 'all') && (
                <Button
                  onClick={() => {
                    setSearchTerm('');
                    setDirectionFilter('all');
                    setSortBy('newest');
                  }}
                  variant="secondary"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-3 mt-6">
              {filteredConversations.map((conv, index) => {
                const directionConfig = getDirectionConfig(conv.direction);
                const DirectionIcon = directionConfig.icon;
                
                return (
                  <div
                    key={`sms-${conv.sms_id}-${index}`}
                    onClick={() => {
                      if (conv.lead_id != null && !isNaN(Number(conv.lead_id))) {
                        // Conversation has lead_id - navigate to detail page
                        navigate(`/sms/${conv.lead_id}?smsId=${conv.sms_id}`);
                      } else if (conv.phone_number) {
                        // Conversation without lead_id - use phone number
                        navigate(`/sms/phone/${encodeURIComponent(conv.phone_number)}?smsId=${conv.sms_id}`);
                      } else {
                        toast.error('Cannot view conversation: Missing lead ID and phone number');
                      }
                    }}
                    className="p-4 bg-dark-elevated border-2 border-dark-border hover:border-primary/40 rounded-xl transition-all duration-200 cursor-pointer hover:scale-[1.01] animate-slide-in-left"
                    style={{ animationDelay: `${index * 0.03}s` }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-3">
                          <Badge variant={directionConfig.color as any} size="sm">
                            <DirectionIcon className="w-3 h-3 mr-1" />
                            {directionConfig.label}
                          </Badge>
                          <div className="flex items-center gap-2 text-sm text-dark-text-muted">
                            <Phone className="w-3 h-3" />
                            <span className="font-mono">{conv.phone_number}</span>
                          </div>
                          {conv.lead_name && (
                            <div className="flex items-center gap-2 text-sm text-dark-text-secondary">
                              <User className="w-3 h-3" />
                              <span>{conv.lead_name}</span>
                            </div>
                          )}
                        </div>
                        
                        <p className="text-sm text-dark-text-primary mb-2 line-clamp-2">
                          {conv.message_content}
                        </p>
                        
                        <div className="flex items-center gap-4 text-xs text-dark-text-muted flex-wrap">
                          {conv.city && conv.state && (
                            <div className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              <span>{conv.city}, {conv.state}</span>
                            </div>
                          )}
                          <div className="flex items-center gap-1" title={conv.created_at ? new Date(conv.created_at).toLocaleString() : 'N/A'}>
                            <Clock className="w-3 h-3" />
                            <span className="font-mono">{formatDate(conv.created_at)}</span>
                          </div>
                          {conv.message_type && (
                            <div className="flex items-center gap-1">
                              <span className="px-2 py-0.5 bg-dark-surface rounded text-xs">
                                {conv.message_type}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex-shrink-0 flex items-center gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (conv.lead_id != null && !isNaN(Number(conv.lead_id))) {
                              // Conversation has lead_id - navigate to detail page
                              navigate(`/sms/${conv.lead_id}?smsId=${conv.sms_id}`);
                            } else if (conv.phone_number) {
                              // Conversation without lead_id - use phone number
                              navigate(`/sms/phone/${encodeURIComponent(conv.phone_number)}?smsId=${conv.sms_id}`);
                            } else {
                              toast.error('Cannot view conversation: Missing lead ID and phone number');
                            }
                          }}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (conv.lead_id != null && !isNaN(Number(conv.lead_id))) {
                              handleDeleteConversation(conv.lead_id, e);
                            } else {
                              toast.error('Cannot delete conversation: Lead ID is missing');
                            }
                          }}
                          className="text-error-light hover:text-error hover:bg-error/10"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      ) : (
        <Card 
          title="Photo Submissions" 
          subtitle={`${filteredPhotos.length} photo${filteredPhotos.length !== 1 ? 's' : ''} found • ${pendingPhotos} pending review`}
          action={
            <div className="flex items-center gap-3">
              {totalPhotos > 0 && (
                <Button
                  onClick={handleDeleteAllPhotos}
                  variant="danger"
                  size="sm"
                  className="animate-scale-in"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete All
                </Button>
              )}
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                <span className="text-xs text-dark-text-muted">
                  Updated {lastUpdate.toLocaleTimeString()}
                </span>
              </div>
            </div>
          }
          className="animate-scale-in"
        >
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 py-8">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="aspect-square bg-dark-elevated border border-dark-border rounded-xl animate-pulse"></div>
              ))}
            </div>
          ) : filteredPhotos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4">
                <Camera className="w-10 h-10 text-dark-text-muted" />
              </div>
              <h3 className="text-lg font-bold text-dark-text-primary mb-2">No photos found</h3>
              <p className="text-sm text-dark-text-muted mb-6 text-center max-w-md">
                {searchTerm || statusFilter !== 'all'
                  ? "No photo submissions match your current filters. Try adjusting your search or filters."
                  : "No photo submissions yet. Photos will appear here when customers submit images."}
              </p>
              {(searchTerm || statusFilter !== 'all') && (
                <Button
                  onClick={() => {
                    setSearchTerm('');
                    setStatusFilter('all');
                    setSortBy('newest');
                  }}
                  variant="secondary"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-6">
              {filteredPhotos.map((photo, index) => {
                const statusConfig = getStatusConfig(photo.status);
                const StatusIcon = statusConfig.icon;
                
                return (
                  <Card
                    key={`photo-${photo.photo_id}-${index}`}
                    className="overflow-hidden hover:scale-105 transition-all duration-300 animate-slide-in-left"
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    {/* Photo */}
                    <div className="aspect-square bg-dark-elevated relative group cursor-pointer" onClick={() => setSelectedPhoto(photo)}>
                      <img
                        src={photo.photo_url}
                        alt="Item photo"
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWUyOTNiIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzY0NzQ4YiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBhdmFpbGFibGU8L3RleHQ+PC9zdmc+';
                        }}
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all duration-200 flex items-center justify-center">
                        <div className="opacity-0 group-hover:opacity-100 transition-all duration-200">
                          <Badge variant="neutral" size="sm" className="bg-white/20 text-white">
                            <Eye className="w-3 h-3 mr-1" />
                            View
                          </Badge>
                        </div>
                      </div>
                      
                      {/* Status Badge */}
                      <div className="absolute top-3 right-3">
                        <Badge variant={statusConfig.color as any} size="sm">
                          <StatusIcon className="w-3 h-3 mr-1" />
                          {statusConfig.label}
                        </Badge>
                      </div>
                    </div>
                    
                    {/* Content */}
                    <div className="p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm text-dark-text-muted">
                          <Phone className="w-3 h-3" />
                          <span className="font-mono text-xs">{photo.phone_number}</span>
                        </div>
                        <span className="text-xs text-dark-text-muted">{formatDate(photo.created_at)}</span>
                      </div>
                      
                      {photo.lead_name && (
                        <div className="flex items-center gap-2 text-sm text-dark-text-secondary">
                          <User className="w-3 h-3" />
                          <span className="font-medium">{photo.lead_name}</span>
                        </div>
                      )}
                      
                      {photo.address && (
                        <div className="flex items-center gap-2 text-xs text-dark-text-muted">
                          <MapPin className="w-3 h-3" />
                          <span className="truncate">{photo.city}, {photo.state}</span>
                        </div>
                      )}
                      
                      {/* Action Buttons */}
                      <div className="flex gap-2 pt-2">
                        {photo.status === 'pending' && (
                          <>
                            <Button
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePhotoStatusUpdate(photo.photo_id, 'reviewed');
                              }}
                              variant="success"
                              className="flex-1"
                            >
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Review
                            </Button>
                            <Button
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePhotoStatusUpdate(photo.photo_id, 'appraised');
                              }}
                              variant="warning"
                              className="flex-1"
                            >
                              <Star className="w-3 h-3 mr-1" />
                              Appraise
                            </Button>
                          </>
                        )}
                        {photo.status === 'reviewed' && (
                          <Button
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handlePhotoStatusUpdate(photo.photo_id, 'appraised');
                            }}
                            variant="warning"
                            className="flex-1"
                          >
                            <Star className="w-3 h-3 mr-1" />
                            Appraise
                          </Button>
                        )}
                        {photo.status === 'appraised' && (
                          <div className="flex-1 text-center py-2">
                            <Badge variant="success" size="sm">
                              <Star className="w-3 h-3 mr-1" />
                              Appraised
                            </Badge>
                          </div>
                        )}
                        <Button
                          size="sm"
                          onClick={(e) => handleDeletePhoto(photo.photo_id, e)}
                          variant="ghost"
                          className="text-error-light hover:text-error hover:bg-error/10"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* Photo Modal */}
      {selectedPhoto && (() => {
        const modalStatusConfig = getStatusConfig(selectedPhoto.status);
        const ModalStatusIcon = modalStatusConfig.icon;
        
        return (
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in"
            onClick={() => setSelectedPhoto(null)}
          >
            <div 
              className="bg-dark-surface rounded-2xl max-w-5xl max-h-[90vh] overflow-hidden border-2 border-dark-border shadow-modern-xl animate-scale-in flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-dark-border flex items-center justify-between flex-shrink-0">
                <h3 className="text-xl font-bold text-dark-text-primary flex items-center gap-3">
                  <ImageIcon className="w-6 h-6 text-primary-light" />
                  Photo Details
                </h3>
                <button
                  onClick={() => setSelectedPhoto(null)}
                  className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Photo */}
                  <div className="space-y-4">
                    <div className="aspect-square bg-dark-elevated rounded-xl overflow-hidden border-2 border-dark-border">
                      <img
                        src={selectedPhoto.photo_url}
                        alt="Item photo"
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWUyOTNiIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzY0NzQ4YiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBhdmFpbGFibGU8L3RleHQ+PC9zdmc+';
                        }}
                      />
                    </div>
                    
                    {/* Photo Info */}
                    <Card>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold text-dark-text-secondary">Photo ID</span>
                          <span className="font-mono text-sm text-dark-text-primary">#{selectedPhoto.photo_id}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold text-dark-text-secondary">Submitted</span>
                          <span className="text-sm text-dark-text-primary">{formatDate(selectedPhoto.created_at)}</span>
                        </div>
                      </div>
                    </Card>
                  </div>
                  
                  {/* Details */}
                  <div className="space-y-6">
                    {/* Contact Information */}
                    <Card>
                      <div className="space-y-4">
                        <h4 className="text-lg font-bold text-dark-text-primary flex items-center gap-2">
                          <User className="w-5 h-5 text-primary-light" />
                          Contact Information
                        </h4>
                        <div className="space-y-3">
                          <div className="flex items-center gap-3">
                            <Phone className="w-4 h-4 text-dark-text-muted" />
                            <span className="font-mono text-dark-text-primary">{selectedPhoto.phone_number}</span>
                          </div>
                          {selectedPhoto.lead_name && (
                            <div className="flex items-center gap-3">
                              <User className="w-4 h-4 text-dark-text-muted" />
                              <span className="text-dark-text-primary">{selectedPhoto.lead_name}</span>
                            </div>
                          )}
                          {selectedPhoto.address && (
                            <div className="flex items-center gap-3">
                              <MapPin className="w-4 h-4 text-dark-text-muted" />
                              <span className="text-dark-text-secondary text-sm">
                                {selectedPhoto.address}, {selectedPhoto.city}, {selectedPhoto.state}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>
                    
                    {/* Status */}
                    <Card>
                      <div className="space-y-4">
                        <h4 className="text-lg font-bold text-dark-text-primary flex items-center gap-2">
                          <Clock className="w-5 h-5 text-primary-light" />
                          Status & Actions
                        </h4>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-dark-text-secondary">Current Status</span>
                            <Badge variant={modalStatusConfig.color as any} size="sm">
                              <ModalStatusIcon className="w-4 h-4 mr-1" />
                              {modalStatusConfig.label}
                            </Badge>
                          </div>
                        {selectedPhoto.reviewed_at && (
                          <div className="flex items-center justify-between">
                            <span className="text-dark-text-secondary">Reviewed</span>
                            <span className="text-sm text-dark-text-primary">{formatDate(selectedPhoto.reviewed_at)}</span>
                          </div>
                        )}
                        {selectedPhoto.reviewed_by && (
                          <div className="flex items-center justify-between">
                            <span className="text-dark-text-secondary">Reviewed By</span>
                            <span className="text-sm text-dark-text-primary">{selectedPhoto.reviewed_by}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                  
                  {/* Actions */}
                  {selectedPhoto.status === 'pending' && (
                    <div className="space-y-3">
                      <h4 className="text-lg font-bold text-dark-text-primary">Quick Actions</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <Button
                          onClick={() => {
                            handlePhotoStatusUpdate(selectedPhoto.photo_id, 'reviewed');
                            setSelectedPhoto(null);
                          }}
                          variant="success"
                          className="flex items-center justify-center gap-2"
                        >
                          <CheckCircle className="w-4 h-4" />
                          Mark as Reviewed
                        </Button>
                        <Button
                          onClick={() => {
                            handlePhotoStatusUpdate(selectedPhoto.photo_id, 'appraised');
                            setSelectedPhoto(null);
                          }}
                          variant="warning"
                          className="flex items-center justify-center gap-2"
                        >
                          <Star className="w-4 h-4" />
                          Mark as Appraised
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
        );
      })()}
    </div>
  );
};

export default SMSPage;
