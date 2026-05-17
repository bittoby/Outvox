// PopupCard Component - Clean & Simple Design
import React, { useState } from 'react';
import { Phone, X, MapPin, Clock, User, AlertCircle, CheckCircle2 } from 'lucide-react';
import Badge from '../Badge/Badge';
import Button from '../Button/Button';
import type { PopupQueueItem } from '../../services/api/popup';
import toast from 'react-hot-toast';

interface PopupCardProps {
  popup: PopupQueueItem;
  onDial: (popup: PopupQueueItem, employeeName: string) => Promise<void>;
  onDismiss: (popupId: number) => Promise<void>;
}

const PopupCard: React.FC<PopupCardProps> = ({ popup, onDial, onDismiss }) => {
  const [dialing, setDialing] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const [employeeName, setEmployeeName] = useState('');
  const isVerified = popup.lead.sms_verified;
  const consentRequestedAt = popup.lead.sms_consent_requested_at;
  const verifiedAt = popup.lead.sms_verified_at;

  const handleDial = async () => {
    if (!employeeName.trim()) {
      toast.error('Please enter your name for compliance tracking');
      return;
    }

    if (!popup.lead.sms_verified) {
      toast.error('SMS consent pending. Please wait for the lead to reply YES before dialing.');
      return;
    }

    setDialing(true);
    try {
      await onDial(popup, employeeName.trim());
      // Success toast is handled in PopupPage
    } catch (error: any) {
      // Error toast is handled in PopupPage, but show here too for immediate feedback
      const errorMsg = error.response?.data?.message || 
                       error.response?.data?.detail || 
                       error.message || 
                       'Failed to dial lead';
      toast.error(errorMsg);
    } finally {
      setDialing(false);
    }
  };

  const handleDismiss = async () => {
    if (!confirm(`Dismiss popup for ${popup.lead.name || popup.lead.phone_number}?`)) {
      return;
    }

    setDismissing(true);
    try {
      await onDismiss(popup.popup_id);
      toast.success('Popup dismissed');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to dismiss popup');
      setDismissing(false);
    }
  };

  const formatTime = (dateString: string | null) => {
    if (!dateString) return 'Just now';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  const getPriorityVariant = (priority: number) => {
    // Priority 5 = Highest, 1 = Lowest
    if (priority === 5) return 'error';
    if (priority === 4) return 'warning';
    if (priority === 3) return 'info';
    if (priority === 2) return 'success';
    return 'neutral';
  };

  return (
    <div className="bg-dark-surface border-2 border-primary/30 rounded-xl p-5 shadow-modern-lg hover:border-primary hover:border-[3px] hover:shadow-glow-primary/20 transition-all duration-300 animate-scale-in group relative overflow-hidden">
      {/* Animated background on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      
      {/* Header */}
      <div className="relative flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 group-hover:scale-110 transition-all duration-300 shadow-lg">
              <User className="w-6 h-6 text-primary-light group-hover:text-primary transition-colors duration-300" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-bold text-dark-text-primary truncate mb-1 group-hover:text-primary-light transition-colors duration-300">
                {popup.lead.name || 'Unknown Name'}
              </h3>
              <div className="flex items-center gap-2 text-sm">
                <Phone className="w-4 h-4 text-dark-text-muted group-hover:text-primary transition-colors duration-300" />
                <span className="font-mono text-dark-text-secondary group-hover:text-dark-text-primary transition-colors duration-300">{popup.lead.phone_number}</span>
              </div>
            </div>
          </div>
          
          {/* Priority Badge */}
          <div className="flex items-center gap-2">
            <Badge variant={getPriorityVariant(popup.lead.priority)} size="sm">
              Priority {popup.lead.priority}
            </Badge>
            {popup.lead.dnc_flag && (
              <Badge variant="neutral" size="sm">
                <AlertCircle className="w-3 h-3 mr-1" />
                DNC
              </Badge>
            )}
            <Badge variant={isVerified ? 'success' : 'warning'} size="sm">
              {isVerified ? (
                <>
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  SMS Verified
                </>
              ) : (
                <>
                  <AlertCircle className="w-3 h-3 mr-1" />
                  Awaiting Consent
                </>
              )}
            </Badge>
          </div>
        </div>
        
        <button
          onClick={handleDismiss}
          disabled={dismissing || dialing}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-danger hover:bg-danger/10 active:scale-95 transition-all duration-200 disabled:opacity-50 hover:rotate-90"
          title="Dismiss"
        >
          <X className="w-4 h-4 transition-transform duration-200" />
        </button>
      </div>

      {/* Address */}
      {(popup.lead.Address || popup.lead.City || popup.lead.State) && (
        <div className="mb-4 flex items-start gap-2 text-sm text-dark-text-secondary hover:text-dark-text-primary transition-colors duration-200 p-2 rounded-lg hover:bg-dark-elevated/30">
          <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0 group-hover:text-primary transition-colors duration-200" />
          <span className="transition-colors duration-200">{[popup.lead.Address, popup.lead.City, popup.lead.State].filter(Boolean).join(', ')}</span>
        </div>
      )}

      {/* Metadata */}
      <div className="flex items-center gap-4 mb-4 text-xs text-dark-text-muted px-2 py-1.5 rounded-lg hover:bg-dark-elevated/30 transition-colors duration-200">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 group-hover:text-primary transition-colors duration-200" />
          <span className="transition-colors duration-200">{formatTime(popup.created_at)}</span>
        </div>
        {popup.lead.call_count > 0 && (
          <span className="transition-colors duration-200">{popup.lead.call_count} previous call{popup.lead.call_count !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* Employee Name Input */}
      <div className="mb-4 animate-fade-in">
        <label className="block text-sm font-semibold text-dark-text-primary mb-2 transition-colors duration-200 group-hover:text-primary-light">
          Your Name <span className="text-danger animate-pulse">*</span>
        </label>
        <input
          type="text"
          value={employeeName}
          onChange={(e) => setEmployeeName(e.target.value)}
          placeholder="Enter your name"
          className="w-full px-4 py-2.5 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 focus:scale-[1.02] rounded-lg text-dark-text-primary placeholder-dark-text-muted transition-all duration-200 outline-none"
          disabled={dialing || dismissing}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter' && employeeName.trim() && !dialing) {
              handleDial();
            }
          }}
        />
        <p className="text-xs text-dark-text-muted mt-1.5 transition-colors duration-200 group-hover:text-dark-text-secondary">Required for TCPA compliance</p>
        {!isVerified && (
          <p className="text-xs text-warning-light mt-2 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Waiting for customer SMS consent{consentRequestedAt ? ` – requested ${formatTime(consentRequestedAt)}` : ''}
          </p>
        )}
        {isVerified && verifiedAt && (
          <p className="text-xs text-dark-text-muted mt-2 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-success-light" />
            Verified {formatTime(verifiedAt)}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3 animate-fade-in">
        <Button
          onClick={handleDial}
          variant="primary"
          className="flex-1 h-11 font-semibold hover:scale-105 active:scale-95 transition-transform duration-200 shadow-lg hover:shadow-glow-primary/30"
          disabled={dialing || dismissing || !employeeName.trim() || !isVerified}
        >
          {dialing ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              Dialing...
            </>
          ) : (
            <>
              <Phone className="w-4 h-4 mr-2 group-hover:animate-pulse" />
              Dial Now
            </>
          )}
        </Button>
        <Button
          onClick={handleDismiss}
          variant="secondary"
          className="h-11 px-4 hover:scale-105 active:scale-95 transition-transform duration-200"
          disabled={dialing || dismissing}
        >
          {dismissing ? (
            <>
              <div className="w-4 h-4 border-2 border-dark-text-primary border-t-transparent rounded-full animate-spin mr-2" />
              Dismissing...
            </>
          ) : (
            <X className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Ready Indicator */}
      {employeeName.trim() && !dialing && (
        <div className="mt-3 flex items-center gap-2 text-xs text-success animate-fade-in">
          <CheckCircle2 className="w-4 h-4 animate-pulse" />
          <span className="font-medium animate-pulse-slow">Ready to dial</span>
        </div>
      )}
    </div>
  );
};

export default PopupCard;
