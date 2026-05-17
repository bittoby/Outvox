// Popup Page - TCPA Compliance: Manual Click-to-Dial
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Phone, AlertCircle, RefreshCw, Users, Search, X } from 'lucide-react';
import Card from '../components/Card/Card';
import PopupCard from '../components/PopupCard/PopupCard';
import { getPendingPopups, dismissPopup, prepareManualDial, dialLead } from '../services/api/popup';
import { useWebSocket, EventType } from '../hooks/useWebSocket';
import type { PopupQueueItem } from '../services/api/popup';
import toast, { Toaster } from 'react-hot-toast';

const PopupPage: React.FC = () => {
  const [popups, setPopups] = useState<PopupQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<'created_at' | 'priority' | 'name'>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [priorityFilter, setPriorityFilter] = useState<'all' | '1' | '2' | '3' | '4' | '5'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const [totalPopups, setTotalPopups] = useState(0);

  // Fetch pending popups
  const fetchPopups = useCallback(async () => {
    try {
      setRefreshing(true);
      const offset = (currentPage - 1) * pageSize;
      const response = await getPendingPopups({
        limit: pageSize,
        offset,
        sort_field: sortField,
        sort_direction: sortDirection,
        priority: priorityFilter !== 'all' ? Number(priorityFilter) : undefined,
      });
      setPopups(response.pending_popups || []);
      setTotalPopups(response.total || 0);
    } catch (error: any) {
      console.error('Error fetching popups:', error);
      toast.error(error.response?.data?.detail || 'Failed to load popups');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [currentPage, pageSize, sortField, sortDirection, priorityFilter]);

  // WebSocket for real-time updates
  const { subscribe, on } = useWebSocket({ autoConnect: true });

  useEffect(() => {
    // Subscribe to popup events
    subscribe([
      EventType.POPUP_ADDED,
      EventType.POPUP_UPDATED,
      EventType.POPUP_DISMISSED,
    ]);

    // Handle popup added
    const unsubscribeAdded = on(EventType.POPUP_ADDED, () => {
      fetchPopups();
    });

    // Handle popup updated
    const unsubscribeUpdated = on(EventType.POPUP_UPDATED, () => {
      fetchPopups();
    });

    // Handle popup dismissed
    const unsubscribeDismissed = on(EventType.POPUP_DISMISSED, () => {
      fetchPopups();
    });

    return () => {
      unsubscribeAdded();
      unsubscribeUpdated();
      unsubscribeDismissed();
    };
  }, [subscribe, on, fetchPopups]);

  // Initial load
  useEffect(() => {
    fetchPopups();
  }, [fetchPopups]);

  // Handle dial action
  const handleDial = async (popup: PopupQueueItem, employeeName: string) => {
    try {
      // Step 1: Actually dial the lead FIRST
      const result = await dialLead({
        lead_id: popup.lead_id,
        employee_name: employeeName,
        popup_id: popup.popup_id
      });

      // Step 2: Only if call succeeded, update popup queue status
      if (result && result.status === 'success') {
        // Now mark as dialed in database
        try {
          await prepareManualDial({
            lead_id: popup.lead_id,
            employee_name: employeeName
          });
        } catch (prepareError) {
          // If prepare fails but call succeeded, log but don't fail
          console.warn('Failed to update popup status, but call succeeded:', prepareError);
        }
        
        // Remove from local state
        setPopups(prev => prev.filter(p => p.popup_id !== popup.popup_id));
        toast.success(`Call initiated successfully! Call SID: ${result.call_sid || 'N/A'}`);
      } else {
        // Don't remove popup on failure - let user try again
        const errorMessage = result?.message || 'Failed to dial lead';
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('Error dialing:', error);
      // Show detailed error message
      const errorMsg = error.response?.data?.message || error.response?.data?.detail || error.message || 'Failed to dial lead';
      toast.error(`Call failed: ${errorMsg}`);
      throw error; // Re-throw to let PopupCard handle the error
    }
  };

  // Handle dismiss action
  const handleDismiss = async (popupId: number) => {
    try {
      await dismissPopup(popupId);
      // Remove from local state
      setPopups(prev => prev.filter(p => p.popup_id !== popupId));
      toast.success('Popup dismissed');
    } catch (error: any) {
      console.error('Error dismissing popup:', error);
      throw error; // Re-throw to let PopupCard handle the error
    }
  };

  // Filter popups based on search query
  const filteredPopups = useMemo(() => {
    if (!searchQuery.trim()) {
      return popups;
    }

    const query = searchQuery.toLowerCase().trim();
    return popups.filter((popup) => {
      const lead = popup.lead;
      const searchableFields = [
        lead.name || '',
        lead.phone_number || '',
        lead.Address || '',
        lead.City || '',
        lead.State || '',
      ].join(' ').toLowerCase();

      return searchableFields.includes(query);
    });
  }, [popups, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(totalPopups / pageSize));

  useEffect(() => {
    if (!loading && currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage, loading]);

  return (
    <div className="max-w-[1600px] mx-auto space-y-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex items-start justify-between animate-slide-in-left">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-white shadow-glow-primary animate-float">
            <Phone className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-primary-light to-primary bg-clip-text text-transparent">
              Click-to-Dial Popup
            </h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              TCPA Compliance: Manual call confirmation required
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchPopups}
            disabled={refreshing}
            className="px-4 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary font-medium transition-all outline-none disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 inline mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Info Banner */}
      <Card>
        <div className="flex items-start gap-4 p-4 bg-info/10 border-2 border-info/20 rounded-lg">
          <AlertCircle className="w-6 h-6 text-info-light flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-dark-text-primary mb-1">TCPA Compliance Notice</h3>
            <p className="text-sm text-dark-text-secondary">
              All outbound calls require manual confirmation from a store employee. 
              Each call is logged with employee name and timestamp for compliance audit trails.
            </p>
          </div>
        </div>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-primary-light" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Pending Popups</p>
              <p className="text-2xl font-bold text-dark-text-primary">
                {searchQuery ? `${filteredPopups.length} / ${totalPopups}` : totalPopups}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Search Bar */}
      {popups.length > 0 && (
        <Card>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Search className="w-5 h-5 text-dark-text-muted" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, phone, address, city, or reason..."
              className="w-full pl-12 pr-12 py-3 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 pr-4 flex items-center text-dark-text-muted hover:text-dark-text-primary transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
          {searchQuery && (
            <p className="mt-2 text-sm text-dark-text-secondary">
              Showing {filteredPopups.length} of {totalPopups} popups
            </p>
          )}
        </Card>
      )}

      {/* Sorting & Filters */}
      {totalPopups > 0 && (
        <Card>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col">
              <label className="text-sm font-semibold text-dark-text-primary mb-2">Sort By</label>
              <div className="flex items-center gap-2">
                <select
                  value={sortField}
                  onChange={(e) => {
                    setSortField(e.target.value as typeof sortField);
                    setCurrentPage(1);
                  }}
                  className="flex-1 px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                >
                  <option value="created_at">Created Time</option>
                  <option value="priority">Priority</option>
                  <option value="name">Lead Name</option>
                </select>
                <button
                  onClick={() => {
                    setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
                    setCurrentPage(1);
                  }}
                  className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary hover:border-primary/30 transition-all"
                >
                  {sortDirection === 'asc' ? 'Asc' : 'Desc'}
                </button>
              </div>
            </div>

            <div className="flex flex-col">
              <label className="text-sm font-semibold text-dark-text-primary mb-2">Priority Filter</label>
              <select
                value={priorityFilter}
                onChange={(e) => {
                  setPriorityFilter(e.target.value as typeof priorityFilter);
                  setCurrentPage(1);
                }}
                className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              >
                <option value="all">All Priorities</option>
                <option value="1">Priority 1</option>
                <option value="2">Priority 2</option>
                <option value="3">Priority 3</option>
                <option value="4">Priority 4</option>
                <option value="5">Priority 5</option>
              </select>
            </div>

            <div className="flex flex-col">
              <label className="text-sm font-semibold text-dark-text-primary mb-2">Go to Page</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min={1}
                  max={totalPages}
                  value={currentPage}
                  onChange={(e) => {
                    const value = Number(e.target.value);
                    if (!Number.isNaN(value)) {
                      setCurrentPage(Math.min(Math.max(1, value), totalPages));
                    }
                  }}
                  className="w-24 px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                <button
                  onClick={() => fetchPopups()}
                  className="px-4 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary font-medium transition-all"
                >
                  Go
                </button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Popup Cards */}
      {loading ? (
        <Card>
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="ml-3 text-dark-text-primary">Loading popups...</span>
          </div>
        </Card>
      ) : popups.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4">
              <Phone className="w-10 h-10 text-dark-text-muted" />
            </div>
            <p className="text-lg font-semibold text-dark-text-primary mb-2">
              No pending popups
            </p>
            <p className="text-sm text-dark-text-muted mb-6">
              New leads will appear here when added to the system
            </p>
          </div>
        </Card>
      ) : filteredPopups.length === 0 && searchQuery ? (
        <Card>
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4">
              <Search className="w-10 h-10 text-dark-text-muted" />
            </div>
            <p className="text-lg font-semibold text-dark-text-primary mb-2">
              No popups found
            </p>
            <p className="text-sm text-dark-text-muted mb-6">
              Try adjusting your search query
            </p>
            <button
              onClick={() => setSearchQuery('')}
              className="px-4 py-2 bg-primary/10 hover:bg-primary/20 border-2 border-primary/30 hover:border-primary/50 rounded-lg text-primary-light font-medium transition-all"
            >
              Clear Search
            </button>
          </div>
        </Card>
      ) : (
        <>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
            <div className="text-sm text-dark-text-muted">
              Page {currentPage} of {totalPages} • Showing {filteredPopups.length} popups
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-dark-text-muted">Per page:</label>
              <select
                value={pageSize}
                onChange={(e) => {
                  setCurrentPage(1);
                  setPageSize(Number(e.target.value));
                }}
                className="px-3 py-1 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              >
                {[15, 30, 60, 100].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => fetchPopups()}
                disabled={refreshing}
                className="px-4 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary font-medium transition-all outline-none disabled:opacity-50"
              >
                Current Page
              </button>
              {[currentPage - 1, currentPage, currentPage + 1]
                .filter((page) => page >= 1 && page <= totalPages)
                .map((page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`px-3 py-2 border-2 rounded-lg text-sm font-semibold transition-all ${
                      page === currentPage
                        ? 'bg-primary/10 border-primary/40 text-primary-light'
                        : 'bg-dark-elevated border-dark-border text-dark-text-primary hover:border-primary/30'
                    }`}
                  >
                    {page}
                  </button>
                ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPopups.map((popup) => (
              <PopupCard
                key={popup.popup_id}
                popup={popup}
                onDial={handleDial}
                onDismiss={handleDismiss}
              />
            ))}
          </div>

          <div className="flex items-center justify-between mt-6">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1 || refreshing}
              className="px-4 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary font-medium transition-all outline-none disabled:opacity-50"
            >
              Previous
            </button>
            <div className="text-sm text-dark-text-muted">
              {totalPopups === 0
                ? 'No popups'
                : `Showing ${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, totalPopups)} of ${totalPopups}`}
            </div>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={currentPage >= totalPages || refreshing}
              className="px-4 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary font-medium transition-all outline-none disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default PopupPage;


