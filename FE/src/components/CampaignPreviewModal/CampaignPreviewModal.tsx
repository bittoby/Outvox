// Campaign Preview Modal - Milestone 14
import React, { useState, useRef, useEffect } from 'react';
import Button from '../Button/Button';
import Card from '../Card/Card';
import Badge from '../Badge/Badge';
import { previewCampaign, startCampaign } from '../../services/api';
import type { CampaignPreviewResponse, StartCampaignResponse } from '../../types/campaign';

interface CampaignPreviewModalProps {
  storeId: number;
  storeName: string;
  onClose: () => void;
  onSuccess: (campaign: StartCampaignResponse) => void;
}

const CampaignPreviewModal: React.FC<CampaignPreviewModalProps> = ({
  storeId,
  storeName,
  onClose,
  onSuccess,
}) => {
  const [step, setStep] = useState<'input' | 'preview' | 'confirm' | 'starting'>('input');
  const [targetCount, setTargetCount] = useState<string>('50');
  const [preview, setPreview] = useState<CampaignPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && step !== 'starting') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose, step]);

  const handlePreview = async () => {
    const count = parseInt(targetCount);
    if (isNaN(count) || count <= 0) {
      setError('Please enter a valid number of leads (greater than 0)');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const previewData = await previewCampaign({
        store_id: storeId,
        target_count: count,
      });

      if (!previewData) {
        throw new Error('Failed to generate preview');
      }

      setPreview(previewData);
      setStep('preview');
    } catch (err: any) {
      setError(err.message || 'Failed to generate campaign preview');
    } finally {
      setLoading(false);
    }
  };

  const handleStartCampaign = async () => {
    if (!preview) return;

    setStep('starting');
    setError(null);

    try {
      const result = await startCampaign({
        store_id: storeId,
        target_count: preview.leads_to_contact,
      });

      onSuccess(result);
    } catch (err: any) {
      setError(err.message || 'Failed to start campaign');
      setStep('confirm');
    }
  };

  const renderInputStep = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-dark-text-primary mb-2">
          Configure New Campaign
        </h2>
        <p className="text-dark-text-secondary">
          How many leads do you want to contact for <strong>{storeName}</strong>?
        </p>
      </div>

      <div>
        <label className="block text-sm font-semibold text-dark-text-primary mb-2">
          Number of Leads to Contact
        </label>
        <input
          type="number"
          value={targetCount}
          onChange={(e) => setTargetCount(e.target.value)}
          min="1"
          className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary-light focus:outline-none transition-colors text-lg"
          placeholder="Enter number of leads..."
        />
        <p className="text-xs text-dark-text-muted mt-2">
          Leads will be contacted via SMS in batches of 25-30
        </p>
      </div>

      {error && (
        <div className="p-4 bg-danger/10 border-2 border-danger/30 rounded-lg">
          <p className="text-danger-light font-semibold">❌ {error}</p>
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="secondary" onClick={onClose} className="flex-1">
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={handlePreview}
          disabled={loading}
          className="flex-1"
        >
          {loading ? '⏳ Loading...' : '👁️ Preview Campaign'}
        </Button>
      </div>
    </div>
  );

  const renderPreviewStep = () => {
    if (!preview) return null;

    return (
      <div className="space-y-6">
        {/* Warning Banner */}
        <div className="p-4 bg-warning/10 border-2 border-warning rounded-lg">
          <div className="flex items-start gap-3">
            <span className="text-3xl">⚠️</span>
            <div>
              <h3 className="text-lg font-bold text-warning-light mb-1">
                This will send SMS and incur charges
              </h3>
              <p className="text-sm text-dark-text-secondary">
                Review the details below carefully before proceeding
              </p>
            </div>
          </div>
        </div>

        {/* Campaign Summary */}
        <Card title="Campaign Summary" variant="primary">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-dark-elevated rounded-lg">
              <p className="text-xs text-dark-text-secondary mb-1">Store</p>
              <p className="text-lg font-bold text-dark-text-primary">{preview.store_name}</p>
            </div>
            <div className="p-3 bg-dark-elevated rounded-lg">
              <p className="text-xs text-dark-text-secondary mb-1">Leads to Contact</p>
              <p className="text-lg font-bold text-primary-light">{preview.leads_to_contact}</p>
            </div>
            <div className="p-3 bg-dark-elevated rounded-lg">
              <p className="text-xs text-dark-text-secondary mb-1">Estimated Cost</p>
              <p className="text-lg font-bold text-success-light">
                ${preview.estimated_cost.toFixed(2)}
              </p>
            </div>
            <div className="p-3 bg-dark-elevated rounded-lg">
              <p className="text-xs text-dark-text-secondary mb-1">Estimated Time</p>
              <p className="text-lg font-bold text-info-light">
                {preview.estimated_time_hours.toFixed(1)} hours
              </p>
            </div>
            <div className="p-3 bg-dark-elevated rounded-lg">
              <p className="text-xs text-dark-text-secondary mb-1">Batches</p>
              <p className="text-lg font-bold text-dark-text-primary">{preview.estimated_batches}</p>
            </div>
            <div className="p-3 bg-dark-elevated rounded-lg">
              <p className="text-xs text-dark-text-secondary mb-1">Available Numbers</p>
              <p className="text-lg font-bold text-dark-text-primary">
                {preview.available_phone_numbers}
              </p>
            </div>
          </div>

          <div className="mt-4 p-3 bg-info/5 border border-info/30 rounded-lg">
            <p className="text-sm text-dark-text-secondary">
              <strong>Batch Size:</strong> {preview.batch_size} SMS per batch
              <br />
              <strong>Batch Spacing:</strong> {preview.batch_spacing_minutes} minutes between batches
            </p>
          </div>
        </Card>

        {/* Preview Leads */}
        <Card title="Preview of Leads" subtitle="First 10 leads to be contacted">
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {preview.preview_leads.map((lead, index) => (
              <div
                key={lead.lead_id}
                className="flex items-center gap-3 p-3 bg-dark-elevated rounded-lg border border-dark-border hover:border-primary/30 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary-light font-bold text-sm">
                  {index + 1}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-dark-text-primary">
                    {lead.name || 'Unknown'}
                  </p>
                  <p className="text-xs text-dark-text-secondary font-mono">
                    {lead.phone_number}
                  </p>
                </div>
                {lead.City && lead.State && (
                  <Badge variant="info">
                    {lead.City}, {lead.State}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </Card>

        {/* Warnings */}
        {preview.warnings && preview.warnings.length > 0 && (
          <Card title="⚠️ Warnings" variant="warning">
            <div className="space-y-2">
              {preview.warnings.map((warning, index) => (
                <div
                  key={index}
                  className="p-3 bg-warning/10 border border-warning/30 rounded-lg"
                >
                  <p className="text-sm text-warning-light font-semibold">{warning}</p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Cost Warning */}
        <div className="p-6 bg-danger/10 border-2 border-danger rounded-lg text-center">
          <div className="text-5xl mb-3">💰</div>
          <h3 className="text-xl font-bold text-danger-light mb-2">
            You will be charged ${preview.estimated_cost.toFixed(2)} immediately
          </h3>
          <p className="text-sm text-dark-text-secondary mb-1">
            This action <strong>cannot be undone</strong>
          </p>
          <p className="text-xs text-dark-text-muted">
            SMS will be sent in batches starting immediately
          </p>
        </div>

        {error && (
          <div className="p-4 bg-danger/10 border-2 border-danger/30 rounded-lg">
            <p className="text-danger-light font-semibold">❌ {error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => setStep('input')} className="flex-1">
            ← Back
          </Button>
          <Button
            variant="danger"
            onClick={() => setStep('confirm')}
            className="flex-1"
          >
            Confirm & Start →
          </Button>
        </div>
      </div>
    );
  };

  const renderConfirmStep = () => {
    if (!preview) return null;

    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="text-6xl mb-4">🚨</div>
          <h2 className="text-2xl font-bold text-danger-light mb-2">
            Final Confirmation
          </h2>
          <p className="text-dark-text-secondary mb-4">
            Are you absolutely sure you want to proceed?
          </p>
        </div>

        <Card variant="danger">
          <div className="text-center space-y-4">
            <div>
              <p className="text-sm text-dark-text-secondary mb-2">You are about to send</p>
              <p className="text-4xl font-bold text-danger-light mb-2">
                {preview.leads_to_contact} SMS
              </p>
              <p className="text-sm text-dark-text-secondary">for a total cost of</p>
              <p className="text-3xl font-bold text-danger-light mt-2">
                ${preview.estimated_cost.toFixed(2)}
              </p>
            </div>

            <div className="p-4 bg-danger/10 border border-danger/30 rounded-lg">
              <p className="text-sm text-dark-text-primary font-semibold">
                ⚠️ This action is <span className="text-danger-light">IRREVERSIBLE</span>
              </p>
              <p className="text-xs text-dark-text-muted mt-1">
                SMS will begin sending immediately and charges will be incurred
              </p>
            </div>
          </div>
        </Card>

        {error && (
          <div className="p-4 bg-danger/10 border-2 border-danger/30 rounded-lg">
            <p className="text-danger-light font-semibold">❌ {error}</p>
          </div>
        )}

        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => setStep('preview')} className="flex-1">
            ← Go Back
          </Button>
          <Button variant="danger" onClick={handleStartCampaign} className="flex-1">
            Yes, Start Campaign 🚀
          </Button>
        </div>
      </div>
    );
  };

  const renderStartingStep = () => (
    <div className="text-center py-12">
      <div className="animate-spin inline-block w-16 h-16 border-4 border-primary-light border-t-transparent rounded-full mb-6"></div>
      <h3 className="text-2xl font-bold text-dark-text-primary mb-2">
        Starting Campaign...
      </h3>
      <p className="text-dark-text-secondary">
        Please wait while we schedule your SMS batches
      </p>
    </div>
  );

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in"
      onClick={(e) => {
        // Close modal when clicking on backdrop (not on modal content)
        if (e.target === e.currentTarget && step !== 'starting') {
          onClose();
        }
      }}
    >
      <div 
        ref={modalRef}
        className="bg-dark-surface border-2 border-dark-border rounded-xl shadow-modern-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 animate-scale-in"
        onClick={(e) => {
          // Prevent closing when clicking inside modal
          e.stopPropagation();
        }}
      >
        {step === 'input' && renderInputStep()}
        {step === 'preview' && renderPreviewStep()}
        {step === 'confirm' && renderConfirmStep()}
        {step === 'starting' && renderStartingStep()}
      </div>
    </div>
  );
};

export default CampaignPreviewModal;

