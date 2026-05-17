// Call History Page - Clean & Modern

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Phone, Clock, TrendingUp, Search, Filter, Trash2, CheckSquare, Square } from 'lucide-react';
import Card from '../components/Card/Card';
import Badge from '../components/Badge/Badge';
import toast, { Toaster } from 'react-hot-toast';
import { getCallHistory, deleteCallHistory } from '../services/api';
import type { CallHistoryItem } from '../types/call';

const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [history, setHistory] = useState<CallHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterResult, setFilterResult] = useState<string>('all');
  const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set());

  // Fetch call history
  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await getCallHistory({
        limit: 100,
        result_type: filterResult !== 'all' ? filterResult : undefined
      });
      setHistory(data);
    } catch (error) {
      console.error('Error fetching call history:', error);
      toast.error('Failed to load call history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterResult]);

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

  const formatDuration = (seconds: number) => {
    if (!seconds || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (timestamp: string) => {
    try {
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date(timestamp));
    } catch {
      return 'N/A';
    }
  };

  const handleDelete = async (e: React.MouseEvent, item: CallHistoryItem) => {
    e.stopPropagation(); // Prevent row click navigation
    
    if (!window.confirm(`Are you sure you want to delete this call record?\n\n${item.lead_name || 'Unknown'} - ${item.phone_number}`)) {
      return;
    }

    try {
      await deleteCallHistory(item.id);
      toast.success('Call record deleted successfully');
      // Refresh the list
      fetchHistory();
      // Remove from selection
      setSelectedItems(prev => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    } catch (error) {
      console.error('Error deleting call history:', error);
      toast.error('Failed to delete call record');
    }
  };

  const toggleSelect = (e: React.MouseEvent, itemId: number) => {
    e.stopPropagation();
    setSelectedItems(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  const toggleSelectAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedItems.size === filteredHistory.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(filteredHistory.map(item => item.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedItems.size === 0) {
      toast.error('Please select at least one record to delete');
      return;
    }

    const confirmMessage = selectedItems.size === 1
      ? `Are you sure you want to delete ${selectedItems.size} call record?`
      : `Are you sure you want to delete ${selectedItems.size} call records?`;

    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      const deletePromises = Array.from(selectedItems).map(id => deleteCallHistory(id));
      await Promise.all(deletePromises);
      toast.success(`Successfully deleted ${selectedItems.size} record(s)`);
      setSelectedItems(new Set());
      fetchHistory();
    } catch (error) {
      console.error('Error deleting call history:', error);
      toast.error('Failed to delete some records');
      fetchHistory();
    }
  };

  const handleDeleteAll = async () => {
    if (filteredHistory.length === 0) {
      toast.error('No records to delete');
      return;
    }

    if (!window.confirm(`⚠️ Are you sure you want to delete ALL ${filteredHistory.length} call records?\n\nThis action cannot be undone!`)) {
      return;
    }

    try {
      const deletePromises = filteredHistory.map(item => deleteCallHistory(item.id));
      await Promise.all(deletePromises);
      toast.success(`Successfully deleted all ${filteredHistory.length} records`);
      setSelectedItems(new Set());
      fetchHistory();
    } catch (error) {
      console.error('Error deleting all records:', error);
      toast.error('Failed to delete some records');
      fetchHistory();
    }
  };

  // Filter history (backend already filters by result_type, we only filter by search here)
  const filteredHistory = history.filter((item) => {
    if (!searchTerm) return true; // No search term, show all
    
    const matchesSearch = (item.lead_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.phone_number.includes(searchTerm) ||
                         item.agent_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const stats = {
    total: history.length,
    interested: history.filter((h) => h.result_type === 'interested').length,
    avgDuration: history.length > 0 ? Math.round(history.reduce((sum, h) => sum + h.call_duration, 0) / history.length) : 0,
  };

  return (
    <div className="max-w-[1600px] mx-auto space-y-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex items-center gap-4 animate-slide-in-left">
        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-warning to-warning-dark flex items-center justify-center text-white shadow-glow-warning animate-float">
          <FileText className="w-7 h-7" />
        </div>
        <div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-warning-light to-warning bg-clip-text text-transparent">
            Call History
          </h1>
          <p className="text-sm text-dark-text-secondary mt-1">
            Review past calls and outcomes
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-dark-surface border-2 border-dark-border hover:border-primary/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Phone className="w-5 h-5 text-primary-light animate-pulse-slow" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Total Calls</p>
              <p className="text-2xl font-bold text-dark-text-primary">{stats.total}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-surface border-2 border-dark-border hover:border-success/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-success-light animate-pulse-slow" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Interested</p>
              <p className="text-2xl font-bold text-dark-text-primary">{stats.interested}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-surface border-2 border-dark-border hover:border-info/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-info-light animate-pulse-slow" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Avg Duration</p>
              <p className="text-2xl font-bold text-dark-text-primary">{formatDuration(stats.avgDuration)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-text-muted" />
            <input
              type="text"
              placeholder="Search by name, phone, or agent..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted text-sm font-medium transition-all outline-none"
            />
          </div>

          {/* Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-dark-text-muted" />
            <select
              value={filterResult}
              onChange={(e) => setFilterResult(e.target.value)}
              className="px-3 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary rounded-lg text-dark-text-primary text-sm font-medium transition-all outline-none cursor-pointer"
            >
              <option value="all">All Results</option>
              <option value="interested">Interested</option>
              <option value="not_interested">Not Interested</option>
              <option value="callback">Callback</option>
              <option value="dnc">DNC</option>
              <option value="completed">Completed</option>
            </select>
          </div>

          {/* Info Button */}
          {history.length > 0 && (
            <button
              onClick={() => toast('Call history is preserved for compliance and audit purposes', { 
                duration: 4000,
                icon: 'ℹ️' 
              })}
              title="Call records cannot be deleted"
              className="flex items-center gap-2 px-4 py-2 bg-info/10 hover:bg-info/20 border-2 border-info/30 hover:border-info/50 text-info-light rounded-lg text-sm font-semibold transition-all hover:scale-105"
            >
              <FileText className="w-4 h-4" />
              Info
            </button>
          )}
        </div>
      </Card>

      {/* History List */}
      <Card 
        title="Call Records" 
        subtitle={`${filteredHistory.length} calls found${selectedItems.size > 0 ? ` • ${selectedItems.size} selected` : ''}`}
        action={
          selectedItems.size > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleBulkDelete}
                className="flex items-center gap-2 px-4 py-2 bg-danger hover:bg-danger-dark text-white rounded-lg text-sm font-semibold transition-all hover:scale-105"
              >
                <Trash2 className="w-4 h-4" />
                Delete Selected ({selectedItems.size})
              </button>
            </div>
          )
        }
      >
        {loading ? (
          <div className="space-y-3 mt-6">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-dark-elevated border border-dark-border rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4">
              <FileText className="w-10 h-10 text-dark-text-muted" />
            </div>
            <p className="text-lg font-semibold text-dark-text-primary mb-2">No calls found</p>
            <p className="text-sm text-dark-text-muted">Try adjusting your search or filter</p>
          </div>
        ) : (
          <div className="mt-6">
            {/* Bulk Actions Bar */}
            {filteredHistory.length > 0 && (
              <div className="flex items-center justify-between mb-4 p-3 bg-dark-elevated border border-dark-border rounded-lg">
                <div className="flex items-center gap-3">
                  <button
                    onClick={toggleSelectAll}
                    className="p-1 rounded-lg text-dark-text-muted hover:text-primary hover:bg-primary/10 transition-all"
                    title={selectedItems.size === filteredHistory.length ? 'Deselect All' : 'Select All'}
                  >
                    {selectedItems.size === filteredHistory.length ? (
                      <CheckSquare className="w-5 h-5" />
                    ) : (
                      <Square className="w-5 h-5" />
                    )}
                  </button>
                  <span className="text-sm text-dark-text-secondary">
                    {selectedItems.size > 0 ? `${selectedItems.size} selected` : 'Select records'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {selectedItems.size > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-3 py-1.5 bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger-light rounded-lg text-sm font-medium transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete Selected
                    </button>
                  )}
                  {filteredHistory.length > 0 && (
                    <button
                      onClick={handleDeleteAll}
                      className="flex items-center gap-2 px-3 py-1.5 bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger-light rounded-lg text-sm font-medium transition-all"
                      title="Delete all visible records"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete All ({filteredHistory.length})
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Table Header */}
            <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-3 bg-dark-elevated border border-dark-border rounded-t-lg">
              <div className="col-span-1">
                <p className="text-xs font-bold text-dark-text-muted uppercase tracking-wide">Select</p>
              </div>
              <div className="col-span-3">
                <p className="text-xs font-bold text-dark-text-muted uppercase tracking-wide">Contact</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs font-bold text-dark-text-muted uppercase tracking-wide">Agent</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs font-bold text-dark-text-muted uppercase tracking-wide">Duration</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs font-bold text-dark-text-muted uppercase tracking-wide">Time</p>
              </div>
              <div className="col-span-1 text-right">
                <p className="text-xs font-bold text-dark-text-muted uppercase tracking-wide">Result</p>
              </div>
              <div className="col-span-1 text-right">
                <p className="text-xs font-bold text-dark-text-muted uppercase tracking-wide">Action</p>
              </div>
            </div>

            {/* Table Body */}
            <div className="space-y-0">
              {filteredHistory.map((item, index) => (
                <div
                  key={item.id}
                  onClick={() => navigate(`/history/${item.id}`)}
                  className={`group grid grid-cols-12 gap-4 items-center p-4 border-x border-b border-dark-border hover:border-primary/30 transition-all duration-200 animate-slide-in-left last:rounded-b-lg cursor-pointer ${
                    selectedItems.has(item.id) 
                      ? 'bg-primary/10 hover:bg-primary/15' 
                      : 'bg-dark-surface hover:bg-dark-elevated'
                  }`}
                  style={{ animationDelay: `${index * 0.02}s` }}
                >
                  {/* Checkbox (1 col) */}
                  <div className="col-span-12 md:col-span-1 flex items-center">
                    <button
                      onClick={(e) => toggleSelect(e, item.id)}
                      className="p-1 rounded-lg text-dark-text-muted hover:text-primary hover:bg-primary/10 transition-all"
                      title={selectedItems.has(item.id) ? 'Deselect' : 'Select'}
                    >
                      {selectedItems.has(item.id) ? (
                        <CheckSquare className="w-5 h-5 text-primary-light" />
                      ) : (
                        <Square className="w-5 h-5" />
                      )}
                    </button>
                  </div>

                  {/* Contact (3 cols) */}
                  <div className="col-span-12 md:col-span-3 flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                      <Phone className="w-5 h-5 text-primary-light" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-dark-text-primary truncate">{item.lead_name || 'Unknown'}</p>
                      <p className="text-xs font-mono text-dark-text-muted truncate">{item.phone_number}</p>
                    </div>
                  </div>

                  {/* Agent (2 cols) */}
                  <div className="col-span-6 md:col-span-2 min-w-0">
                    <p className="text-xs font-medium text-dark-text-muted mb-1 md:hidden">Agent</p>
                    <p className="text-sm font-semibold text-dark-text-primary">{item.agent_id}</p>
                  </div>

                  {/* Duration (2 cols) */}
                  <div className="col-span-6 md:col-span-2 min-w-0">
                    <p className="text-xs font-medium text-dark-text-muted mb-1 md:hidden">Duration</p>
                    <p className="text-sm font-mono font-bold text-info-light">{formatDuration(item.call_duration)}</p>
                  </div>

                  {/* Time (2 cols) */}
                  <div className="col-span-6 md:col-span-2 min-w-0">
                    <p className="text-xs font-medium text-dark-text-muted mb-1 md:hidden">Time</p>
                    <p className="text-sm text-dark-text-secondary">{formatDate(item.timestamp)}</p>
                  </div>

                  {/* Result Badge (1 col) */}
                  <div className="col-span-6 md:col-span-1 flex justify-start md:justify-end">
                    {getResultBadge(item.result_type)}
                  </div>

                  {/* Actions (1 col) */}
                  <div className="col-span-6 md:col-span-1 flex justify-start md:justify-end gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/history/${item.id}`);
                      }}
                      title="View call details"
                      className="p-2 rounded-lg text-dark-text-muted hover:text-primary hover:bg-primary/10 transition-all"
                    >
                      <FileText className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(e, item)}
                      title="Delete call record"
                      className="p-2 rounded-lg text-dark-text-muted hover:text-danger hover:bg-danger/10 transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default HistoryPage;
