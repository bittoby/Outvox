// SMS Conversation Detail Page - Detailed view of SMS conversation

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { 
  ArrowLeft, Phone, Clock, User, MessageSquare, 
  MapPin, Calendar, Mail, ArrowUp, ArrowDown
} from 'lucide-react';
import Card from '../components/Card/Card';
import Badge from '../components/Badge/Badge';
import toast, { Toaster } from 'react-hot-toast';
import { getSMSConversationDetails, getSMSConversationDetailsByPhone, SMSConversationDetails } from '../services/api/sms';

const SMSConversationDetailPage: React.FC = () => {
  const { id, phoneNumber } = useParams<{ id?: string; phoneNumber?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [conversationDetails, setConversationDetails] = useState<SMSConversationDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [highlightedSmsId, setHighlightedSmsId] = useState<number | null>(null);
  const highlightedRef = useRef<HTMLDivElement | null>(null);

  const fetchConversationDetails = useCallback(async (leadId: number) => {
    try {
      setLoading(true);
      const data = await getSMSConversationDetails(leadId);
      setConversationDetails(data);
    } catch (error) {
      console.error('Error fetching SMS conversation details:', error);
      toast.error('Failed to load conversation details');
      navigate('/sms');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  const fetchConversationDetailsByPhone = useCallback(async (phoneNumber: string) => {
    try {
      setLoading(true);
      const data = await getSMSConversationDetailsByPhone(phoneNumber);
      setConversationDetails(data);
    } catch (error) {
      console.error('Error fetching SMS conversation details by phone:', error);
      toast.error('Failed to load conversation details');
      navigate('/sms');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    // Get smsId from query parameter if provided
    const smsIdParam = searchParams.get('smsId');
    if (smsIdParam) {
      const smsId = parseInt(smsIdParam);
      if (!isNaN(smsId)) {
        setHighlightedSmsId(smsId);
      }
    }
    
    // Check if we're using phone number or lead ID
    if (phoneNumber) {
      // Conversation without lead_id - fetch by phone number
      const decodedPhone = decodeURIComponent(phoneNumber);
      fetchConversationDetailsByPhone(decodedPhone);
    } else if (id) {
      // Conversation with lead_id - fetch by lead ID
      const leadId = parseInt(id);
      // Validate that leadId is a valid number
      if (isNaN(leadId)) {
        toast.error('Invalid conversation ID');
        navigate('/sms');
        return;
      }
      fetchConversationDetails(leadId);
    }
  }, [
    id,
    phoneNumber,
    searchParams,
    navigate,
    fetchConversationDetails,
    fetchConversationDetailsByPhone,
  ]);

  const formatDate = (timestamp?: string) => {
    if (!timestamp) return { date: 'N/A', time: 'N/A', full: 'N/A' };
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
          minute: '2-digit',
          second: '2-digit'
        }).format(date),
        full: date.toLocaleString('en-US')
      };
    } catch {
      return { date: 'N/A', time: 'N/A', full: 'N/A' };
    }
  };

  const getDirectionConfig = (direction: 'inbound' | 'outbound') => {
    return direction === 'inbound' 
      ? { 
          color: 'text-success-light bg-success/20 border-success/40', 
          icon: ArrowDown, 
          label: 'Incoming',
          bgColor: 'bg-success/10'
        }
      : { 
          color: 'text-primary-light bg-primary/20 border-primary/40', 
          icon: ArrowUp, 
          label: 'Outgoing',
          bgColor: 'bg-primary/10'
        };
  };

  // Scroll to highlighted message when component mounts or highlightedSmsId changes
  useEffect(() => {
    if (highlightedSmsId && highlightedRef.current) {
      setTimeout(() => {
        highlightedRef.current?.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
      }, 300); // Small delay to ensure content is rendered
    }
  }, [highlightedSmsId, conversationDetails]);

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-bg p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-12 bg-dark-surface rounded-lg"></div>
            <div className="h-64 bg-dark-surface rounded-lg"></div>
            <div className="h-96 bg-dark-surface rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!conversationDetails) {
    return (
      <div className="min-h-screen bg-dark-bg p-6">
        <div className="max-w-7xl mx-auto">
          <Card>
            <div className="text-center py-16">
              <p className="text-lg font-semibold text-dark-text-primary mb-2">Conversation not found</p>
              <button
                onClick={() => navigate('/sms')}
                className="text-primary-light hover:text-primary transition-colors"
              >
                ← Back to SMS
              </button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  const { lead_info, conversations } = conversationDetails;
  const dateInfo = conversations.length > 0 ? formatDate(conversations[0].created_at) : null;

  return (
    <div className="min-h-screen bg-dark-bg p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <Toaster position="top-right" />
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/sms')}
              className="p-2 rounded-lg bg-dark-surface hover:bg-dark-elevated border-2 border-dark-border hover:border-primary/40 transition-all hover:scale-105"
            >
              <ArrowLeft className="w-5 h-5 text-dark-text-primary" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-dark-text-primary">SMS Conversation</h1>
              {lead_info && (
                <p className="text-sm text-dark-text-secondary mt-1">
                  {lead_info.name || 'Unknown'} • {lead_info.phone_number}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Lead Information */}
        {lead_info && (
          <Card title="Contact Information" variant="primary">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <User className="w-5 h-5 text-primary-light" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Name</p>
                    <p className="text-lg font-bold text-dark-text-primary">{lead_info.name || 'Unknown'}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Phone className="w-5 h-5 text-primary-light" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Phone</p>
                    <p className="text-lg font-mono font-bold text-dark-text-primary">{lead_info.phone_number}</p>
                  </div>
                </div>

                {lead_info.address && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <MapPin className="w-5 h-5 text-primary-light" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Address</p>
                      <p className="text-sm font-semibold text-dark-text-primary">
                        {lead_info.address}
                        {lead_info.city && `, ${lead_info.city}`}
                        {lead_info.state && `, ${lead_info.state}`}
                        {lead_info.zip && ` ${lead_info.zip}`}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
                    <Calendar className="w-5 h-5 text-info-light" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Created</p>
                    <p className="text-sm font-semibold text-dark-text-primary">
                      {lead_info.created_at ? formatDate(lead_info.created_at).full : 'N/A'}
                    </p>
                  </div>
                </div>

                {lead_info.last_called && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
                      <Clock className="w-5 h-5 text-info-light" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Last Called</p>
                      <p className="text-sm font-semibold text-dark-text-primary">
                        {formatDate(lead_info.last_called).full}
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
                    <Mail className="w-5 h-5 text-warning-light" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Priority</p>
                    <Badge variant={lead_info.priority === 1 ? 'warning' : 'neutral'} size="sm">
                      {lead_info.priority === 1 ? 'High' : 'Normal'}
                    </Badge>
                    {lead_info.dnc_flag && (
                      <Badge variant="error" size="sm" className="ml-2">DNC</Badge>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Conversation Messages */}
        <Card 
          title="Conversation History" 
          subtitle={`${conversations.length} message${conversations.length !== 1 ? 's' : ''} • ${dateInfo ? `Started ${dateInfo.date} at ${dateInfo.time}` : ''}`}
          variant="primary"
        >
          {conversations.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-10 h-10 text-dark-text-muted" />
              </div>
              <p className="text-lg font-semibold text-dark-text-primary mb-2">No messages found</p>
              <p className="text-sm text-dark-text-muted">This conversation has no messages yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conversations.map((message, index) => {
                const directionConfig = getDirectionConfig(message.direction);
                const DirectionIcon = directionConfig.icon;
                const msgDate = formatDate(message.created_at);
                const isOutbound = message.direction === 'outbound';
                const isHighlighted = highlightedSmsId === message.sms_id;

                return (
                  <div
                    key={message.sms_id}
                    ref={isHighlighted ? highlightedRef : null}
                    className={`p-4 rounded-lg border-2 transition-all duration-200 animate-fade-in-up ${
                      isHighlighted
                        ? isOutbound
                          ? 'bg-primary/20 border-primary border-4 ml-8 shadow-glow-primary ring-4 ring-primary/30'
                          : 'bg-success/20 border-success border-4 mr-8 shadow-glow-success ring-4 ring-success/30'
                        : isOutbound
                          ? 'bg-primary/5 border-primary/20 ml-8'
                          : 'bg-success/5 border-success/20 mr-8'
                    }`}
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div className="flex items-center gap-2">
                        {isHighlighted && (
                          <div className="px-2 py-1 bg-primary/30 text-primary-light rounded text-xs font-bold animate-pulse">
                            SELECTED
                          </div>
                        )}
                        <div className={`p-1.5 rounded-lg ${directionConfig.bgColor}`}>
                          <DirectionIcon className={`w-4 h-4 ${directionConfig.color.includes('text-') ? directionConfig.color.split(' ')[0] : 'text-primary-light'}`} />
                        </div>
                        <Badge variant={isOutbound ? 'info' : 'success'} size="sm">
                          {directionConfig.label}
                        </Badge>
                        {message.message_type && (
                          <span className="text-xs text-dark-text-muted px-2 py-1 bg-dark-elevated rounded">
                            {message.message_type}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-dark-text-muted">
                        <Clock className="w-3 h-3" />
                        <span>{msgDate.full}</span>
                      </div>
                    </div>
                    
                    <div className="mt-3">
                      <p className="text-sm text-dark-text-primary whitespace-pre-wrap break-words">
                        {message.message_content}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default SMSConversationDetailPage;
