// Stores Management Page
import React, { useState, useEffect } from 'react';
import {
  Store,
  CheckCircle2,
  RefreshCw,
  Search,
  Plus,
  Edit,
  X,
  Users,
  PhoneCall,
  Trash2
} from 'lucide-react';
import Card from '../components/Card/Card';
import Button from '../components/Button/Button';
import Badge from '../components/Badge/Badge';
import { getStores, createStore, updateStore, deleteStore } from '../services/api/stores';
import type { Store as StoreType } from '../types/lead';
import toast, { Toaster } from 'react-hot-toast';

interface StoreWithStats extends StoreType {
  total_leads?: number;
  total_phone_numbers?: number;
  sms_sent_today?: number;
  calls_made_today?: number;
}

const StoresPage: React.FC = () => {
  const [stores, setStores] = useState<StoreWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingStore, setEditingStore] = useState<StoreWithStats | null>(null);
  const [selectedStores, setSelectedStores] = useState<Set<number>>(new Set());
  const [formData, setFormData] = useState({
    name: '',
    location: '',
    // Quotas are calculated automatically based on phone numbers
    is_active: true
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getStores();
      setStores(data);
    } catch (error) {
      console.error('Error loading stores:', error);
      toast.error('Failed to load stores');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('Store name is required');
      return;
    }

    try {
      toast.loading('Creating store...', { id: 'create-store' });
      await createStore({
        name: formData.name.trim(),
        location: formData.location.trim() || undefined
      });
      toast.success('Store created successfully!', { id: 'create-store' });
      setShowCreateModal(false);
      setFormData({ name: '', location: '', is_active: true });
      await loadData();
    } catch (error: any) {
      console.error('Create error:', error);
      toast.error(error.message || 'Failed to create store', { id: 'create-store' });
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!editingStore) return;
    
    if (!formData.name.trim()) {
      toast.error('Store name is required');
      return;
    }

    try {
      toast.loading('Updating store...', { id: 'update-store' });
      await updateStore(editingStore.store_id, {
        name: formData.name.trim(),
        location: formData.location.trim() || undefined,
        // Quotas are calculated automatically - not needed in update
        is_active: formData.is_active
      });
      toast.success('Store updated successfully!', { id: 'update-store' });
      setShowEditModal(false);
      setEditingStore(null);
      await loadData();
    } catch (error: any) {
      console.error('Update error:', error);
      toast.error(error.message || 'Failed to update store', { id: 'update-store' });
    }
  };

  const openEditModal = (store: StoreWithStats) => {
    setEditingStore(store);
    setFormData({
      name: store.name,
      location: store.location || '',
      // Quotas are calculated automatically - not editable
      is_active: store.is_active
    });
    setShowEditModal(true);
  };

  const handleDelete = async (store: StoreWithStats) => {
    if (!confirm(`Are you sure you want to delete "${store.name}"?\n\nThis will unassign ${store.total_leads || 0} leads and ${store.total_phone_numbers || 0} phone numbers from this store.`)) {
      return;
    }

    try {
      toast.loading('Deleting store...', { id: 'delete-store' });
      const result = await deleteStore(store.store_id);
      toast.success(
        `Store deleted! Unassigned: ${result.unassigned.leads} leads, ${result.unassigned.phone_numbers} phone numbers`,
        { id: 'delete-store', duration: 5000 }
      );
      setSelectedStores(new Set());
      await loadData();
    } catch (error: any) {
      console.error('Delete error:', error);
      toast.error(error.message || 'Failed to delete store', { id: 'delete-store' });
    }
  };

  const handleSelectAll = () => {
    if (selectedStores.size === filteredStores.length) {
      setSelectedStores(new Set());
    } else {
      setSelectedStores(new Set(filteredStores.map(store => store.store_id)));
    }
  };

  const handleToggleSelect = (storeId: number) => {
    const newSelected = new Set(selectedStores);
    if (newSelected.has(storeId)) {
      newSelected.delete(storeId);
    } else {
      newSelected.add(storeId);
    }
    setSelectedStores(newSelected);
  };

  const handleDeleteSelected = async () => {
    if (selectedStores.size === 0) return;
    
    const confirmMessage = `Are you sure you want to delete ${selectedStores.size} selected store(s)?\n\nThis will unassign all leads and phone numbers from these stores.`;
    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      toast.loading(`Deleting ${selectedStores.size} store(s)...`, { id: 'bulk-delete-stores' });
      
      const deletePromises = Array.from(selectedStores).map(storeId => deleteStore(storeId));
      await Promise.all(deletePromises);
      
      toast.success(`${selectedStores.size} store(s) deleted successfully!`, { id: 'bulk-delete-stores' });
      setSelectedStores(new Set());
      await loadData();
    } catch (error: any) {
      console.error('Bulk delete error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete stores';
      toast.error(errorMessage, { id: 'bulk-delete-stores' });
    }
  };

  const handleDeleteAll = async () => {
    if (filteredStores.length === 0) return;
    
    const confirmMessage = `Are you sure you want to delete ALL ${filteredStores.length} store(s)?\n\nThis will unassign all leads and phone numbers from all stores.`;
    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      toast.loading(`Deleting all ${filteredStores.length} store(s)...`, { id: 'delete-all-stores' });
      
      const deletePromises = filteredStores.map(store => deleteStore(store.store_id));
      await Promise.all(deletePromises);
      
      toast.success(`All ${filteredStores.length} store(s) deleted successfully!`, { id: 'delete-all-stores' });
      setSelectedStores(new Set());
      await loadData();
    } catch (error: any) {
      console.error('Delete all error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete all stores';
      toast.error(errorMessage, { id: 'delete-all-stores' });
    }
  };

  const filteredStores = stores.filter(store => {
    const matchesSearch = store.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         store.location?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const activeCount = stores.filter(s => s.is_active).length;
  const totalLeads = stores.reduce((sum, s) => sum + (s.total_leads || 0), 0);
  const totalPhoneNumbers = stores.reduce((sum, s) => sum + (s.total_phone_numbers || 0), 0);

  return (
    <div className="max-w-[1400px] mx-auto space-y-6 p-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-success to-success-dark flex items-center justify-center text-white shadow-glow-success animate-float">
            <Store className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-success-light to-success bg-clip-text text-transparent">
              Stores
            </h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              Manage store locations, quotas, and assignments
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button onClick={() => { setShowCreateModal(true); setFormData({ name: '', location: '', is_active: true }); }} variant="success">
            <Plus className="w-4 h-4" />
            Add Store
          </Button>
          {filteredStores.length > 0 && (
            <Button onClick={handleDeleteAll} variant="danger" title="Delete all stores">
              <Trash2 className="w-4 h-4" />
              Delete All
            </Button>
          )}
          <Button onClick={loadData} variant="secondary">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Total Stores</p>
              <p className="text-2xl font-bold text-dark-text-primary">{stores.length}</p>
            </div>
            <Store className="w-8 h-8 text-success" />
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Active</p>
              <p className="text-2xl font-bold text-success">{activeCount}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-success" />
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Total Leads</p>
              <p className="text-2xl font-bold text-primary-light">{totalLeads}</p>
            </div>
            <Users className="w-8 h-8 text-primary-light" />
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Phone Numbers</p>
              <p className="text-2xl font-bold text-info">{totalPhoneNumbers}</p>
            </div>
            <PhoneCall className="w-8 h-8 text-info" />
          </div>
        </Card>
      </div>

      {/* Search */}
      <Card className="p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
          <input
            type="text"
            placeholder="Search stores by name or location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none"
          />
        </div>
      </Card>

      {/* Bulk Actions */}
      {selectedStores.size > 0 && (
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <Store className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-semibold text-dark-text-primary">
                  {selectedStores.size} store{selectedStores.size !== 1 ? 's' : ''} selected
                </p>
                <p className="text-sm text-dark-text-secondary">Bulk actions available</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleDeleteSelected}
                variant="danger"
                size="sm"
              >
                <Trash2 className="w-4 h-4" />
                Delete Selected
              </Button>
              <Button
                onClick={() => setSelectedStores(new Set())}
                variant="secondary"
                size="sm"
              >
                <X className="w-4 h-4" />
                Clear Selection
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Stores Table */}
      <Card 
        title="Stores" 
        subtitle={`${filteredStores.length} store(s) found${selectedStores.size > 0 ? ` • ${selectedStores.size} selected` : ''}`}
        noPadding
      >
        {loading ? (
          <div className="p-6 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-dark-elevated border border-dark-border rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : filteredStores.length === 0 ? (
          <div className="p-12 text-center">
            <Store className="w-16 h-16 text-dark-text-muted mx-auto mb-4" />
            <p className="text-lg font-semibold text-dark-text-primary mb-2">No stores found</p>
            <p className="text-sm text-dark-text-muted">
              {searchTerm ? 'Try adjusting your search' : 'Add your first store to get started'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-dark-elevated border-b-2 border-dark-border">
                <tr>
                  <th className="text-center py-3 px-4 w-12">
                    <input
                      type="checkbox"
                      checked={selectedStores.size === filteredStores.length && filteredStores.length > 0}
                      onChange={handleSelectAll}
                      className="w-4 h-4 rounded border-dark-border bg-dark-elevated text-primary focus:ring-2 focus:ring-primary cursor-pointer"
                      title="Select all"
                    />
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-dark-text-primary">Store</th>
                  <th className="text-left py-3 px-4 font-semibold text-dark-text-primary">Location</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Status</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Leads</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Phone</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">SMS Quota</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Call Quota</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredStores.map((store) => (
                  <tr key={store.store_id} className="border-b border-dark-border hover:bg-dark-elevated/30 transition-colors">
                    <td className="py-3 px-4 text-center">
                      <input
                        type="checkbox"
                        checked={selectedStores.has(store.store_id)}
                        onChange={() => handleToggleSelect(store.store_id)}
                        className="w-4 h-4 rounded border-dark-border bg-dark-elevated text-primary focus:ring-2 focus:ring-primary cursor-pointer"
                      />
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Store className="w-4 h-4 text-success" />
                        <span className="font-medium text-dark-text-primary">{store.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-dark-text-secondary">{store.location || 'N/A'}</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant={store.is_active ? 'success' : 'error'}>
                        {store.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Users className="w-4 h-4 text-primary-light" />
                        <span className="font-medium text-dark-text-primary">{store.total_leads || 0}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <PhoneCall className="w-4 h-4 text-info" />
                        <span className="font-medium text-dark-text-primary">{store.total_phone_numbers || 0}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex flex-col items-center">
                        <span className="text-sm font-medium text-dark-text-primary">
                          {store.sms_sent_today || 0} / {store.daily_sms_quota || 0}
                        </span>
                        <div className="text-xs text-dark-text-muted mt-1">
                          ({store.total_phone_numbers || 0} × 50)
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex flex-col items-center">
                        <span className="text-sm font-medium text-dark-text-primary">
                          {store.calls_made_today || 0} / {store.daily_call_quota || 0}
                        </span>
                        <div className="text-xs text-dark-text-muted mt-1">
                          ({store.total_phone_numbers || 0} × 30)
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          onClick={() => openEditModal(store)}
                          variant="secondary"
                          size="sm"
                          title="Edit store"
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          onClick={() => handleDelete(store)}
                          variant="danger"
                          size="sm"
                          title="Delete store"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="max-w-md w-full">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-dark-text-primary">Create New Store</h2>
              <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                <X className="w-5 h-5" />
              </Button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-text-primary mb-2">
                  Store Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none"
                  placeholder="e.g., Sunset Store"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-dark-text-primary mb-2">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full px-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none"
                  placeholder="e.g., 100 Main St, Anytown, USA 00001"
                />
              </div>
              <div className="bg-info/10 border border-info/30 rounded-lg p-4">
                <p className="text-sm text-dark-text-primary">
                  <strong>Note:</strong> SMS and Call quotas are calculated automatically based on assigned phone numbers.
                  <br />
                  Each phone number provides: <strong>50 SMS/day</strong> and <strong>30 calls/day</strong>.
                  <br />
                  Assign phone numbers to stores on the Phone Numbers page to increase quotas.
                </p>
              </div>
              <div className="flex gap-3 pt-4">
                <Button type="submit" variant="success" className="flex-1">
                  Create Store
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && editingStore && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="max-w-md w-full">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-dark-text-primary">Edit Store</h2>
              <Button variant="ghost" size="sm" onClick={() => { setShowEditModal(false); setEditingStore(null); }}>
                <X className="w-5 h-5" />
              </Button>
            </div>
            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-text-primary mb-2">
                  Store Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-dark-text-primary mb-2">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full px-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none"
                />
              </div>
              <div className="bg-info/10 border border-info/30 rounded-lg p-4">
                <p className="text-sm text-dark-text-primary">
                  <strong>Note:</strong> SMS and Call quotas are calculated automatically based on assigned phone numbers.
                  <br />
                  Each phone number provides: <strong>50 SMS/day</strong> and <strong>30 calls/day</strong>.
                  <br />
                  Current quotas: <strong>{editingStore?.daily_sms_quota || 0} SMS/day</strong> and <strong>{editingStore?.daily_call_quota || 0} calls/day</strong> ({editingStore?.total_phone_numbers || 0} phone numbers).
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-dark-border bg-dark-elevated text-primary focus:ring-primary"
                />
                <label htmlFor="is_active" className="text-sm font-medium text-dark-text-primary">
                  Active
                </label>
              </div>
              <div className="flex gap-3 pt-4">
                <Button type="submit" variant="primary" className="flex-1">
                  Update Store
                </Button>
                <Button type="button" variant="secondary" onClick={() => { setShowEditModal(false); setEditingStore(null); }}>
                  Cancel
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
};

export default StoresPage;

