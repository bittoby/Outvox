// Phone Numbers Management Page
import React, { useState, useEffect } from 'react';
import {
  Phone,
  Store as StoreIcon,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Search,
  Filter,
  Edit,
  Trash2,
  X,
  ChevronDown,
  Check
} from 'lucide-react';
import Card from '../components/Card/Card';
import Button from '../components/Button/Button';
import Badge from '../components/Badge/Badge';
import { getAllPhoneNumbers, assignPhoneToStore, unassignPhoneFromStore, deletePhoneNumber, deletePhoneNumbers } from '../services/api/phoneNumbers';
import { getStores } from '../services/api/stores';
import type { PhoneNumber } from '../services/api/phoneNumbers';
import type { Store } from '../types/lead';
import toast, { Toaster } from 'react-hot-toast';

const PhoneNumbersPage: React.FC = () => {
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStoreId, setFilterStoreId] = useState<number | null>(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedPhone, setSelectedPhone] = useState<PhoneNumber | null>(null);
  const [assignStoreId, setAssignStoreId] = useState<number | null>(null);
  const [isAssignDropdownOpen, setIsAssignDropdownOpen] = useState(false);
  const [selectedPhones, setSelectedPhones] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [phonesData, storesData] = await Promise.all([
        getAllPhoneNumbers(),
        getStores()
      ]);
      setPhoneNumbers(phonesData);
      setStores(storesData);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load phone numbers');
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async () => {
    if (!selectedPhone || assignStoreId === null || assignStoreId === undefined) {
      toast.error('Please select a store', { id: 'assign-phone' });
      return;
    }

    try {
      toast.loading('Assigning phone number...', { id: 'assign-phone' });
      await assignPhoneToStore(selectedPhone.phone_number_id, assignStoreId);
      toast.success('Phone number assigned successfully!', { id: 'assign-phone' });
      setShowAssignModal(false);
      setSelectedPhone(null);
      setAssignStoreId(null);
      setIsAssignDropdownOpen(false);
      // Force refresh data after assignment
      await loadData();
    } catch (error: any) {
      console.error('Assign error:', error);
      toast.error(error.message || 'Failed to assign phone number', { id: 'assign-phone' });
    }
  };

  const handleUnassign = async (phone: PhoneNumber) => {
    if (!confirm(`Unassign ${phone.phone_number} from ${phone.store_name || 'store'}?`)) return;

    try {
      toast.loading('Unassigning phone number...', { id: 'unassign-phone' });
      await unassignPhoneFromStore(phone.phone_number_id);
      toast.success('Phone number unassigned successfully!', { id: 'unassign-phone' });
      // Force refresh data after unassignment
      await loadData();
    } catch (error: any) {
      console.error('Unassign error:', error);
      toast.error(error.message || 'Failed to unassign phone number', { id: 'unassign-phone' });
    }
  };

  const handleDelete = async (phone: PhoneNumber) => {
    if (!confirm(`⚠️ Are you sure you want to delete phone number ${phone.phone_number}?\n\nThis action cannot be undone!`)) return;

    try {
      toast.loading('Deleting phone number...', { id: 'delete-phone' });
      await deletePhoneNumber(phone.phone_number);
      toast.success('Phone number deleted successfully!', { id: 'delete-phone' });
      await loadData();
    } catch (error: any) {
      console.error('Delete error:', error);
      toast.error(error.message || 'Failed to delete phone number', { id: 'delete-phone' });
    }
  };

  const handleBulkDelete = async () => {
    if (selectedPhones.size === 0) {
      toast.error('Please select at least one phone number to delete');
      return;
    }

    const selectedPhoneNumbers = phoneNumbers
      .filter(p => selectedPhones.has(p.phone_number_id))
      .map(p => p.phone_number);

    if (!confirm(`⚠️ Are you sure you want to delete ${selectedPhones.size} phone number(s)?\n\nThis action cannot be undone!`)) return;

    try {
      toast.loading(`Deleting ${selectedPhones.size} phone number(s)...`, { id: 'bulk-delete' });
      const result = await deletePhoneNumbers(selectedPhoneNumbers);
      
      if (result.failed === 0) {
        toast.success(`Successfully deleted ${result.success} phone number(s)!`, { id: 'bulk-delete' });
      } else {
        toast.success(`Deleted ${result.success} phone number(s). ${result.failed} failed.`, { id: 'bulk-delete' });
        if (result.errors.length > 0) {
          console.error('Delete errors:', result.errors);
        }
      }
      
      setSelectedPhones(new Set());
      await loadData();
    } catch (error: any) {
      console.error('Bulk delete error:', error);
      toast.error(error.message || 'Failed to delete phone numbers', { id: 'bulk-delete' });
    }
  };

  const handleDeleteAll = async () => {
    if (filteredPhones.length === 0) {
      toast.error('No phone numbers to delete');
      return;
    }

    if (!confirm(`⚠️ Are you sure you want to delete ALL ${filteredPhones.length} phone number(s)?\n\nThis action cannot be undone!`)) return;

    try {
      const allPhoneNumbers = filteredPhones.map(p => p.phone_number);
      toast.loading(`Deleting all ${filteredPhones.length} phone number(s)...`, { id: 'delete-all' });
      const result = await deletePhoneNumbers(allPhoneNumbers);
      
      if (result.failed === 0) {
        toast.success(`Successfully deleted all ${result.success} phone number(s)!`, { id: 'delete-all' });
      } else {
        toast.success(`Deleted ${result.success} phone number(s). ${result.failed} failed.`, { id: 'delete-all' });
        if (result.errors.length > 0) {
          console.error('Delete errors:', result.errors);
        }
      }
      
      setSelectedPhones(new Set());
      await loadData();
    } catch (error: any) {
      console.error('Delete all error:', error);
      toast.error(error.message || 'Failed to delete all phone numbers', { id: 'delete-all' });
    }
  };

  const handleSelectPhone = (phoneId: number) => {
    const newSelected = new Set(selectedPhones);
    if (newSelected.has(phoneId)) {
      newSelected.delete(phoneId);
    } else {
      newSelected.add(phoneId);
    }
    setSelectedPhones(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedPhones.size === filteredPhones.length) {
      setSelectedPhones(new Set());
    } else {
      setSelectedPhones(new Set(filteredPhones.map(p => p.phone_number_id)));
    }
  };

  const openAssignModal = (phone: PhoneNumber) => {
    setSelectedPhone(phone);
    setAssignStoreId(phone.store_id);
    setShowAssignModal(true);
  };

  const filteredPhones = phoneNumbers.filter(phone => {
    const matchesSearch = phone.phone_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         phone.store_name?.toLowerCase().includes(searchTerm.toLowerCase());
    // Handle filter: null = all stores, -1 = unassigned only, number = specific store
    let matchesStore = true;
    if (filterStoreId === null) {
      matchesStore = true; // Show all
    } else if (filterStoreId === -1) {
      matchesStore = phone.store_id === null || phone.store_id === undefined; // Unassigned only
    } else {
      matchesStore = phone.store_id === filterStoreId; // Specific store
    }
    return matchesSearch && matchesStore;
  });

  const unassignedCount = phoneNumbers.filter(p => !p.store_id).length;
  const assignedCount = phoneNumbers.filter(p => p.store_id).length;
  const activeCount = phoneNumbers.filter(p => p.is_active).length;

  return (
    <div className="max-w-[1400px] mx-auto space-y-6 p-6">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-white shadow-glow-primary animate-float">
            <Phone className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-primary-light to-primary bg-clip-text text-transparent">
              Phone Numbers
            </h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              Manage Twilio phone numbers and store assignments
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={loadData} variant="secondary">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          {filteredPhones.length > 0 && (
            <Button 
              onClick={handleDeleteAll} 
              variant="danger"
              className="animate-scale-in"
            >
              <Trash2 className="w-4 h-4" />
              Delete All
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Total Numbers</p>
              <p className="text-2xl font-bold text-dark-text-primary">{phoneNumbers.length}</p>
            </div>
            <Phone className="w-8 h-8 text-primary-light" />
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Assigned</p>
              <p className="text-2xl font-bold text-success">{assignedCount}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-success" />
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Unassigned</p>
              <p className="text-2xl font-bold text-warning">{unassignedCount}</p>
            </div>
            <AlertCircle className="w-8 h-8 text-warning" />
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted">Active</p>
              <p className="text-2xl font-bold text-primary-light">{activeCount}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-primary-light" />
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
            <input
              type="text"
              placeholder="Search by phone number or store..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
            <select
              value={filterStoreId === null ? '' : filterStoreId === -1 ? 'unassigned' : filterStoreId}
              onChange={(e) => {
                const value = e.target.value;
                if (value === '') {
                  setFilterStoreId(null); // All stores
                } else if (value === 'unassigned') {
                  setFilterStoreId(-1); // Unassigned only
                } else {
                  setFilterStoreId(Number(value)); // Specific store
                }
              }}
              className="pl-10 pr-8 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none appearance-none cursor-pointer"
            >
              <option value="">All Stores</option>
              <option value="unassigned">Unassigned</option>
              {stores.map(store => (
                <option key={store.store_id} value={store.store_id}>
                  {store.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Bulk Actions */}
      {selectedPhones.size > 0 && (
        <Card className="animate-slide-in-left">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm font-semibold text-dark-text-primary">
                {selectedPhones.size} phone number{selectedPhones.size !== 1 ? 's' : ''} selected
              </span>
              <Button
                onClick={handleBulkDelete}
                variant="danger"
                size="sm"
              >
                <Trash2 className="w-4 h-4" />
                Delete Selected ({selectedPhones.size})
              </Button>
            </div>
            <button
              onClick={() => setSelectedPhones(new Set())}
              className="text-sm text-dark-text-muted hover:text-dark-text-primary transition-colors"
            >
              Clear Selection
            </button>
          </div>
        </Card>
      )}

      {/* Phone Numbers Table */}
      <Card title="Phone Numbers" subtitle={`${filteredPhones.length} number(s) found`} noPadding>
        {loading ? (
          <div className="p-6 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-dark-elevated border border-dark-border rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : filteredPhones.length === 0 ? (
          <div className="p-12 text-center">
            <Phone className="w-16 h-16 text-dark-text-muted mx-auto mb-4" />
            <p className="text-lg font-semibold text-dark-text-primary mb-2">No phone numbers found</p>
            <p className="text-sm text-dark-text-muted">
              {searchTerm || filterStoreId ? 'Try adjusting your filters' : 'Add phone numbers to get started'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-dark-elevated border-b-2 border-dark-border">
                <tr>
                  <th className="text-center py-3 px-4" style={{ width: '50px' }}>
                    <input
                      type="checkbox"
                      checked={selectedPhones.size === filteredPhones.length && filteredPhones.length > 0}
                      onChange={handleSelectAll}
                      className="w-4 h-4 text-primary bg-dark-elevated border-2 border-dark-border rounded focus:ring-primary focus:ring-2"
                    />
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-dark-text-primary">Phone Number</th>
                  <th className="text-left py-3 px-4 font-semibold text-dark-text-primary">Store</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Status</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">SMS Today</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Calls Today</th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPhones.map((phone) => (
                  <tr key={phone.phone_number_id} className="border-b border-dark-border hover:bg-dark-elevated/30 transition-colors">
                    <td className="py-3 px-4 text-center">
                      <input
                        type="checkbox"
                        checked={selectedPhones.has(phone.phone_number_id)}
                        onChange={() => handleSelectPhone(phone.phone_number_id)}
                        className="w-4 h-4 text-primary bg-dark-elevated border-2 border-dark-border rounded focus:ring-primary focus:ring-2"
                      />
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Phone className="w-4 h-4 text-primary-light" />
                        <span className="font-medium text-dark-text-primary">{phone.phone_number}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {phone.store_name ? (
                        <div className="flex items-center gap-2">
                          <StoreIcon className="w-4 h-4 text-info" />
                          <div>
                            <div className="font-medium text-dark-text-primary">{phone.store_name}</div>
                            <div className="text-xs text-dark-text-muted">Store ID: {phone.store_id}</div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-dark-text-muted italic">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant={phone.is_active ? 'success' : 'error'}>
                        {phone.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="text-dark-text-primary">{phone.daily_sms_count}/50</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="text-dark-text-primary">{phone.daily_call_count}/30</span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          onClick={() => openAssignModal(phone)}
                          variant="secondary"
                          size="sm"
                          className="px-3 py-1 text-xs"
                        >
                          <Edit className="w-3 h-3" />
                          {phone.store_id ? 'Reassign' : 'Assign'}
                        </Button>
                        {phone.store_id && (
                          <Button
                            onClick={() => handleUnassign(phone)}
                            variant="warning"
                            size="sm"
                            className="px-3 py-1 text-xs"
                          >
                            <X className="w-3 h-3" />
                            Unassign
                          </Button>
                        )}
                        <Button
                          onClick={() => handleDelete(phone)}
                          variant="danger"
                          size="sm"
                          className="px-3 py-1 text-xs"
                        >
                          <Trash2 className="w-3 h-3" />
                          Delete
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

      {/* Assign Modal */}
      {showAssignModal && selectedPhone && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={() => setShowAssignModal(false)}
        >
          <div
            className="w-full max-w-md bg-dark-surface border-2 border-dark-border rounded-2xl shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-6 border-b border-dark-border">
              <div>
                <h2 className="text-xl font-bold text-dark-text-primary">Assign Phone Number</h2>
                <p className="text-sm text-dark-text-muted mt-1">{selectedPhone.phone_number}</p>
              </div>
              <button
                onClick={() => setShowAssignModal(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                    Select Store *
                  </label>
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setIsAssignDropdownOpen(!isAssignDropdownOpen)}
                      className="w-full px-4 py-3 pl-12 pr-10 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary focus:border-primary focus:outline-none transition-all hover:border-primary/50 font-medium text-left flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        {assignStoreId ? (
                          <>
                            <StoreIcon className="absolute left-4 w-4 h-4 text-primary-light" />
                            <span className="truncate">
                              {stores.find(s => s.store_id === assignStoreId)?.name || 'Select store...'}
                            </span>
                          </>
                        ) : (
                          <span className="text-dark-text-muted">Choose a store...</span>
                        )}
                      </div>
                      <ChevronDown className={`w-4 h-4 text-dark-text-muted transition-transform ${isAssignDropdownOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {isAssignDropdownOpen && (
                      <div className="absolute z-50 w-full mt-2 bg-dark-elevated border-2 border-dark-border rounded-lg shadow-xl max-h-64 overflow-y-auto">
                        <button
                          type="button"
                          onClick={() => {
                            setAssignStoreId(null);
                            setIsAssignDropdownOpen(false);
                          }}
                          className={`w-full px-4 py-3 text-left hover:bg-primary/10 transition-colors flex items-center justify-between ${
                            !assignStoreId ? 'bg-primary/5 border-l-2 border-primary-light' : ''
                          }`}
                        >
                          <span className="text-dark-text-muted italic">Unassigned</span>
                          {!assignStoreId && <Check className="w-4 h-4 text-primary-light" />}
                        </button>
                        {stores.map((store) => (
                          <button
                            key={store.store_id}
                            type="button"
                            onClick={() => {
                              setAssignStoreId(store.store_id);
                              setIsAssignDropdownOpen(false);
                            }}
                            className={`w-full px-4 py-3 text-left hover:bg-primary/10 transition-colors flex items-center justify-between ${
                              assignStoreId === store.store_id ? 'bg-primary/5 border-l-2 border-primary-light' : ''
                            }`}
                          >
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-dark-text-primary">{store.name}</div>
                              <div className="text-xs text-dark-text-muted truncate">{store.location}</div>
                            </div>
                            {assignStoreId === store.store_id && <Check className="w-4 h-4 text-primary-light" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-info/10 border border-info/30 rounded-lg p-4">
                  <p className="text-sm text-dark-text-primary">
                    <strong>Note:</strong> Phone numbers must be assigned to stores before starting SMS campaigns.
                    Each store needs at least 3 phone numbers for proper rotation and carrier compliance.
                  </p>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-dark-border flex gap-3">
              <Button
                onClick={() => setShowAssignModal(false)}
                variant="secondary"
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleAssign}
                variant="primary"
                className="flex-1"
                disabled={assignStoreId === null || assignStoreId === undefined}
              >
                {assignStoreId !== null && assignStoreId !== undefined && selectedPhone?.store_id === assignStoreId ? 'Update' : 'Assign'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PhoneNumbersPage;

