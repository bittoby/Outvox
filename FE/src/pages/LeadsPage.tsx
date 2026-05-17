// Leads Page - Clean, Simple & Modern

import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Phone,
  MapPin,
  X,
  Users,
  TrendingUp,
  Clock,
  CheckCircle2,
  Edit,
  Trash2,
  MoreVertical,
  Upload,
  Download,
  FileText,
  Store as StoreIcon,
  ChevronDown,
  Check,
  Sparkles,
} from 'lucide-react';
import Card from '../components/Card/Card';
import Badge from '../components/Badge/Badge';
import Button from '../components/Button/Button';
import { getLeads, addLead, updateLead, deleteLead, getStores, bulkAssignLeadsToStore, autoAssignLeads } from '../services/api';
import { deleteAllLeads } from '../services/api/leads';
import { importLeadsFromCSV, exportLeadsToCSV } from '../services/api/leads';
import type { Lead, AddLeadRequest, Store } from '../types/lead';
import { parseCSVToLeads, downloadCSV, readFileAsText, validateCSVFormat } from '../utils/csvUtils';
import toast, { Toaster } from 'react-hot-toast';

const LeadsPage: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [activeMenu, setActiveMenu] = useState<number | null>(null);
  const [sortField, setSortField] = useState<keyof Lead>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);
  const [selectedLeads, setSelectedLeads] = useState<Set<number>>(new Set());
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importPreview, setImportPreview] = useState<any[]>([]);
  const [importing, setImporting] = useState(false);
  
  // Milestone 2 & 12: Store management
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStoreFilter, setSelectedStoreFilter] = useState<string>('all');
  const [showBulkAssignModal, setShowBulkAssignModal] = useState(false);
  const [bulkAssignStoreId, setBulkAssignStoreId] = useState<number | null>(null);
  const [isAssignDropdownOpen, setIsAssignDropdownOpen] = useState(false);
  const [showAutoAssignModal, setShowAutoAssignModal] = useState(false);

  // Form state
  const [newLead, setNewLead] = useState<AddLeadRequest>({
    phone_number: '',
    name: '',
    Address: '',
    City: '',
    County: '',
    State: '',
    Zip: '',
    priority: 1,
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      // Check if click is outside dropdown menu
      if (activeMenu !== null && !target.closest('.dropdown-menu') && !target.closest('.dropdown-trigger')) {
        setActiveMenu(null);
      }
    };
    
    if (activeMenu !== null) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [activeMenu]);

  // Fetch leads
  const fetchLeads = async () => {
    try {
      setLoading(true);
      const data = await getLeads({ limit: 5000 });
      setLeads(data);
    } catch {
      toast.error('Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
    fetchStores();
  }, []);
  
  // Fetch stores (Milestone 2)
  const fetchStores = async () => {
    try {
      const data = await getStores();
      setStores(data);
    } catch {
      toast.error('Failed to load stores');
    }
  };

  // Handle add lead
  const handleAddLead = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      toast.loading('Adding lead...', { id: 'add-lead' });
      await addLead(newLead);
      toast.success('Lead added successfully!', { id: 'add-lead' });
      setShowAddModal(false);
      setNewLead({ phone_number: '', name: '', Address: '', City: '', County: '', State: '', Zip: '', priority: 1 });
      // Reload leads without resetting page
      await fetchLeads();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to add lead';
      toast.error(errorMessage, {
        id: 'add-lead',
      });
    }
  };

  // Handle edit lead
  const handleEditLead = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('🔧 handleEditLead called', editingLead);
    if (!editingLead) return;
    
    try {
      toast.loading('Updating lead...', { id: 'edit-lead' });
      await updateLead(editingLead.lead_id, {
        name: editingLead.name,
        phone_number: editingLead.phone_number,
        Address: editingLead.Address,
        City: editingLead.City,
        County: editingLead.County,
        State: editingLead.State,
        Zip: editingLead.Zip,
        priority: editingLead.priority,
        dnc_flag: editingLead.dnc_flag,
      });
      toast.success('Lead updated successfully!', { id: 'edit-lead' });
      setShowEditModal(false);
      setEditingLead(null);
      fetchLeads();
    } catch (error: unknown) {
      console.error('❌ Edit lead error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to update lead';
      toast.error(errorMessage, {
        id: 'edit-lead',
      });
    }
  };

  // Handle delete lead
  const handleDeleteLead = async (leadId: number, leadName: string) => {
    console.log('🗑️ handleDeleteLead called', { leadId, leadName });
    if (!confirm(`Are you sure you want to delete "${leadName}"?`)) {
      console.log('❌ Delete cancelled by user');
      return;
    }
    
    try {
      toast.loading('Deleting lead...', { id: 'delete-lead' });
      await deleteLead(leadId);
      toast.success('Lead deleted successfully!', { id: 'delete-lead' });
      setActiveMenu(null);
      fetchLeads();
    } catch (error: unknown) {
      console.error('❌ Delete lead error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete lead';
      toast.error(errorMessage, {
        id: 'delete-lead',
      });
    }
  };

  // Open edit modal
  const openEditModal = (lead: Lead) => {
    console.log('✏️ openEditModal called', lead);
    setEditingLead(lead);
    setShowEditModal(true);
    setActiveMenu(null);
  };

  // Handle CSV file upload
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please select a CSV file');
      return;
    }

    try {
      const csvContent = await readFileAsText(file);
      const validation = validateCSVFormat(csvContent);
      
      if (!validation.valid) {
        toast.error(validation.error || 'Invalid CSV format');
        return;
      }

      const parsedLeads = parseCSVToLeads(csvContent);
      if (parsedLeads.length === 0) {
        toast.error('No valid leads found in CSV file');
        return;
      }

      setImportFile(file);
      setImportPreview(parsedLeads);
      setShowImportModal(true);
    } catch {
      toast.error('Error reading CSV file');
    }
  };

  // Handle CSV import
  const handleCSVImport = async () => {
    if (!importFile || importPreview.length === 0) return;

    setImporting(true);
    try {
      const csvContent = await readFileAsText(importFile);
      const result = await importLeadsFromCSV(csvContent);
      
      // Show detailed results with context
      const totalAttempted = result.success + result.failed;
      
      if (result.success > 0 && result.failed === 0) {
        // All succeeded
        toast.success(
          `✅ Successfully imported all ${result.success} lead${result.success !== 1 ? 's' : ''}!`,
          { duration: 4000 }
        );
      } else if (result.success > 0 && result.failed > 0) {
        // Partial success
        toast.success(
          `✅ Imported ${result.success} of ${totalAttempted} lead${totalAttempted !== 1 ? 's' : ''} successfully!`,
          { duration: 5000 }
        );
      } else if (result.success === 0 && result.failed > 0) {
        // All failed
        toast.error(
          `❌ Failed to import any leads. Check console for errors.`,
          { duration: 6000 }
        );
      }
      
      // Show errors if any
      if (result.failed > 0 || (result.errors && result.errors.length > 0)) {
        const errorDetails = result.invalid_rows 
          ? result.invalid_rows.map(r => `Row ${r.row} (Phone: ${r.phone}): ${r.error}`).join('\n')
          : result.errors?.join('\n') || 'Unknown errors';
        
        // Clean, consolidated console output (use console.log instead of console.error for info)
        console.group('📋 CSV Import - Skipped Invalid Rows');
        console.log(errorDetails);
        console.groupEnd();
        
        // Build detailed message for toast
        const firstError = result.invalid_rows?.[0];
        const errorSummary = firstError 
          ? `Row ${firstError.row}: ${firstError.error}${result.failed > 1 ? ` (+${result.failed - 1} more)` : ''}`
          : `${result.failed} invalid row${result.failed !== 1 ? 's' : ''}`;
        
        toast(
          `⚠️ Skipped ${errorSummary}`,
          { 
            duration: 6000
          }
        );
      }
      
      // Show duplicates warning
      if (result.duplicates && result.duplicates > 0) {
        toast(
          `ℹ️ Skipped ${result.duplicates} duplicate phone number${result.duplicates !== 1 ? 's' : ''}`,
          { duration: 4000 }
        );
      }
      
      setShowImportModal(false);
      setImportFile(null);
      setImportPreview([]);
      // Reload leads without resetting page
      await fetchLeads();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to import leads';
      toast.error(errorMessage);
    } finally {
      setImporting(false);
    }
  };

  // Handle CSV export
  const handleCSVExport = async () => {
    try {
      toast.loading('Exporting leads...', { id: 'export-leads' });
      const csvContent = await exportLeadsToCSV();
      downloadCSV(csvContent, `leads-export-${new Date().toISOString().split('T')[0]}.csv`);
      toast.success('Leads exported successfully!', { id: 'export-leads' });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to export leads';
      toast.error(errorMessage, { id: 'export-leads' });
    }
  };

  // Filter and sort leads (includes store filtering - Milestone 12)
  const filteredLeads = leads
    .filter(
    (lead) => {
      // Search filter
      const matchesSearch = lead.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.phone_number.includes(searchTerm);
      
      // Store filter
      let matchesStore = true;
      if (selectedStoreFilter === 'unassigned') {
        matchesStore = !lead.store_id;
      } else if (selectedStoreFilter !== 'all') {
        matchesStore = lead.store_id === parseInt(selectedStoreFilter);
      }
      
      return matchesSearch && matchesStore;
    }
    )
    .sort((a, b) => {
      // Special handling for status (dnc_flag) sorting
      if (sortField === 'dnc_flag') {
        const aDNC = a.dnc_flag ? 1 : 0;
        const bDNC = b.dnc_flag ? 1 : 0;
        
        if (sortDirection === 'asc') {
          // Ascending: Active (false/0) first, then DNC (true/1)
          return aDNC - bDNC;
        } else {
          // Descending: DNC (true/1) first, then Active (false/0)
          return bDNC - aDNC;
        }
      }
      
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }

      if (typeof aValue === 'boolean' && typeof bValue === 'boolean') {
        const aBool = aValue ? 1 : 0;
        const bBool = bValue ? 1 : 0;
        return sortDirection === 'asc' ? aBool - bBool : bBool - aBool;
      }
      
      return 0;
    });

  // Pagination logic
  const totalPages = Math.ceil(filteredLeads.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedLeads = filteredLeads.slice(startIndex, endIndex);

  // Reset to first page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  // Reset to first page when sort changes
  useEffect(() => {
    setCurrentPage(1);
  }, [sortField, sortDirection]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.dropdown-menu') && !target.closest('.dropdown-trigger')) {
        setActiveMenu(null);
      }
    };

    if (activeMenu !== null) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [activeMenu]);

  // Get DNC badge
  const getDNCBadge = (dncFlag: boolean) => {
    return dncFlag ? (
      <Badge variant="neutral" size="sm">Do Not Call</Badge>
    ) : (
      <Badge variant="success" size="sm">Active</Badge>
    );
  };

  const getConsentBadge = (lead: Lead) => {
    if (lead.sms_verified) {
      return (
        <div className="flex flex-col items-center gap-1">
          <Badge variant="success" size="sm">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            SMS Verified
          </Badge>
          {lead.sms_verified_at && (
            <span className="text-[10px] text-dark-text-muted">
              {new Date(lead.sms_verified_at).toLocaleString()}
            </span>
          )}
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center gap-1">
        <Badge variant="warning" size="sm">
          <Clock className="w-3 h-3 mr-1" />
          Awaiting Consent
        </Badge>
        {lead.sms_consent_requested_at && (
          <span className="text-[10px] text-dark-text-muted">
            Requested {new Date(lead.sms_consent_requested_at).toLocaleString()}
          </span>
        )}
      </div>
    );
  };
  
  // Milestone 12: Get store badge
  const getStoreBadge = (storeId: number | null) => {
    if (!storeId) {
      return <Badge variant="neutral" size="sm">Unassigned</Badge>;
    }
    
    const store = stores.find(s => s.store_id === storeId);
    return (
      <Badge variant="info" size="sm">
        {store?.name || `Store ${storeId}`}
      </Badge>
    );
  };

  // Handle sorting
  const handleSort = (field: keyof Lead) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Get sort icon
  const getSortIcon = (field: keyof Lead) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  // Bulk operations
  const handleSelectAll = () => {
    if (selectedLeads.size === paginatedLeads.length) {
      setSelectedLeads(new Set());
    } else {
      setSelectedLeads(new Set(paginatedLeads.map(lead => lead.lead_id)));
    }
  };

  const handleSelectLead = (leadId: number) => {
    const newSelected = new Set(selectedLeads);
    if (newSelected.has(leadId)) {
      newSelected.delete(leadId);
    } else {
      newSelected.add(leadId);
    }
    setSelectedLeads(newSelected);
  };

  const handleBulkDelete = async () => {
    if (selectedLeads.size === 0) return;
    
    const confirmMessage = `Are you sure you want to delete ${selectedLeads.size} selected leads?`;
    if (!confirm(confirmMessage)) return;
    
    try {
      toast.loading(`Deleting ${selectedLeads.size} leads...`, { id: 'bulk-delete' });
      
      // Delete leads in parallel
      const deletePromises = Array.from(selectedLeads).map(leadId => deleteLead(leadId));
      await Promise.all(deletePromises);
      
      toast.success(`${selectedLeads.size} leads deleted successfully!`, { id: 'bulk-delete' });
      setSelectedLeads(new Set());
      fetchLeads();
    } catch (error: unknown) {
      console.error('❌ Bulk delete error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete leads';
      toast.error(errorMessage, { id: 'bulk-delete' });
    }
  };

  const handleDeleteAllLeads = async () => {
    if (!confirm('Are you sure you want to delete ALL leads? This cannot be undone.')) {
      return;
    }

    try {
      toast.loading('Deleting all leads...', { id: 'delete-all' });
      await deleteAllLeads();
      toast.success('All leads deleted successfully!', { id: 'delete-all' });
      setSelectedLeads(new Set());
      fetchLeads();
    } catch (error: unknown) {
      console.error('❌ Delete all leads error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete all leads';
      toast.error(errorMessage, { id: 'delete-all' });
    }
  };

  const handleBulkMarkDNC = async () => {
    if (selectedLeads.size === 0) return;
    
    try {
      toast.loading(`Marking ${selectedLeads.size} leads as DNC...`, { id: 'bulk-dnc' });
      
      // Update leads in parallel
      const updatePromises = Array.from(selectedLeads).map(leadId => 
        updateLead(leadId, { dnc_flag: true })
      );
      await Promise.all(updatePromises);
      
      toast.success(`${selectedLeads.size} leads marked as DNC!`, { id: 'bulk-dnc' });
      setSelectedLeads(new Set());
      fetchLeads();
    } catch (error: unknown) {
      console.error('❌ Bulk DNC error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to mark leads as DNC';
      toast.error(errorMessage, { id: 'bulk-dnc' });
    }
  };
  
  // Milestone 12: Bulk assign to store
  const handleBulkAssignToStore = async () => {
    if (selectedLeads.size === 0 || !bulkAssignStoreId) return;
    
    try {
      toast.loading(`Assigning ${selectedLeads.size} leads to store...`, { id: 'bulk-assign' });
      
      const result = await bulkAssignLeadsToStore(Array.from(selectedLeads), bulkAssignStoreId);
      
      toast.success(result.message, { id: 'bulk-assign' });
      setSelectedLeads(new Set());
      setShowBulkAssignModal(false);
      setBulkAssignStoreId(null);
      setIsAssignDropdownOpen(false);
      fetchLeads();
    } catch (error: unknown) {
      console.error('❌ Bulk assign error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to assign leads';
      toast.error(errorMessage, { id: 'bulk-assign' });
    }
  };

  // Auto-assign leads based on location
  const handleAutoAssign = async () => {
    try {
      toast.loading('Auto-assigning leads to stores...', { id: 'auto-assign' });
      const result = await autoAssignLeads();
      
      if (result.success) {
        toast.success(
          `✅ Auto-assigned ${result.assigned_count} leads to stores. ${result.skipped_count} skipped (no location match).`,
          { id: 'auto-assign', duration: 5000 }
        );
        setShowAutoAssignModal(false);
        fetchLeads();
      } else {
        toast.error(result.message || 'Failed to auto-assign leads', { id: 'auto-assign' });
      }
    } catch (error: any) {
      console.error('❌ Auto-assign error:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to auto-assign leads';
      toast.error(errorMessage, { id: 'auto-assign', duration: 5000 });
    }
  };

  // Stats
  const totalLeads = leads.length;
  const activeLeads = leads.filter((l) => !l.dnc_flag).length;
  const unassignedLeads = leads.filter((l) => !l.store_id).length;

  return (
    <div className="w-full max-w-[1600px] mx-auto space-y-6 px-4" style={{ overflowX: 'hidden', boxSizing: 'border-box' }}>
      <Toaster position="top-right" />

      {/* Clean Header */}
      <div className="flex items-start justify-between animate-slide-in-left">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-info to-info-dark flex items-center justify-center text-white shadow-glow-info animate-float">
            <Users className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-dark-text-primary via-info-light to-info bg-clip-text text-transparent">
              Leads
            </h1>
            <p className="text-sm text-dark-text-secondary mt-1">
              Manage and track your calling leads
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Import Button */}
          <div className="relative">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              id="csv-upload"
            />
            <label
              htmlFor="csv-upload"
              className="inline-flex items-center justify-center px-4 py-2 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary font-medium transition-all outline-none cursor-pointer animate-scale-in"
            >
              <Upload className="w-4 h-4" />
              <span>Import CSV</span>
            </label>
          </div>
          
          {/* Export Button */}
          <Button
            onClick={handleCSVExport}
            variant="secondary"
            className="animate-scale-in"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </Button>
          
          {/* Auto-Assign Button - Enhanced */}
          <button
            onClick={() => setShowAutoAssignModal(true)}
            className="relative inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 hover:from-purple-500 hover:via-pink-500 hover:to-orange-400 text-white font-semibold rounded-lg shadow-lg shadow-purple-500/50 transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-purple-500/70 animate-scale-in overflow-hidden group"
          >
            {/* Animated background shimmer */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
            
            {/* Sparkles icon with pulse animation */}
            <Sparkles className="w-4 h-4 relative z-10 animate-pulse" />
            <span className="relative z-10">Auto-Assign</span>
            
            {/* Glowing effect */}
            <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-300 -z-10"></div>
          </button>

          {/* Delete All Button */}
          <Button
            onClick={handleDeleteAllLeads}
            variant="danger"
            className="animate-scale-in"
          >
            <Trash2 className="w-4 h-4" />
            <span>Delete All</span>
          </Button>  
          
          {/* Add Lead Button */}
        <Button
          onClick={() => setShowAddModal(true)}
          variant="primary"
          className="animate-scale-in"
        >
          <Plus className="w-5 h-5" />
          <span>Add Lead</span>
        </Button>
        </div>
      </div>

      {/* Stats Cards - Clean & Simple */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-dark-surface border-2 border-dark-border hover:border-primary/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-primary-light animate-pulse-slow" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Total Leads</p>
              <p className="text-2xl font-bold text-dark-text-primary">{totalLeads}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-surface border-2 border-dark-border hover:border-warning/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
              <StoreIcon className="w-5 h-5 text-warning-light animate-pulse-slow" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Unassigned Leads</p>
              <p className="text-2xl font-bold text-dark-text-primary">{unassignedLeads}</p>
            </div>
          </div>
        </div>

        <div className="bg-dark-surface border-2 border-dark-border hover:border-success/40 rounded-xl p-5 transition-all duration-300 hover:scale-105 card-glow animate-slide-in-left stagger-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-success-light animate-pulse-slow" />
            </div>
            <div>
              <p className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide">Active Leads</p>
              <p className="text-2xl font-bold text-dark-text-primary">{activeLeads}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Sort Controls */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search Bar */}
          <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
          <input
            type="text"
            placeholder="Search leads by name or phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-xl text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
          />
          </div>
          
          {/* Store Filter (Milestone 12) */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-dark-text-muted whitespace-nowrap">Store:</span>
            <select
              value={selectedStoreFilter}
              onChange={(e) => setSelectedStoreFilter(e.target.value)}
              className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none min-w-[140px]"
            >
              <option value="all">All Stores</option>
              <option value="unassigned">Unassigned</option>
              {stores.map(store => (
                <option key={store.store_id} value={store.store_id}>
                  {store.name}
                </option>
              ))}
            </select>
          </div>
          
          {/* Sort Controls */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-dark-text-muted whitespace-nowrap">Sort by:</span>
            <select
              value={sortField}
              onChange={(e) => setSortField(e.target.value as keyof Lead)}
              className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
            >
              <option value="name">Name</option>
              <option value="phone_number">Phone</option>
              <option value="priority">Priority</option>
              <option value="call_count">Calls</option>
              <option value="dnc_flag">Status</option>
              <option value="last_called">Last Called</option>
            </select>
            <button
              onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
              className="p-2 bg-dark-elevated border-2 border-dark-border rounded-lg hover:border-primary/30 transition-colors"
            >
              {sortDirection === 'asc' ? '↑' : '↓'}
            </button>
            <button
              onClick={() => {
                setSortField('name');
                setSortDirection('asc');
              }}
              className="px-3 py-2 bg-dark-surface border-2 border-dark-border rounded-lg hover:border-primary/30 transition-colors text-sm text-dark-text-muted"
            >
              Clear
            </button>
          </div>
        </div>
      </Card>

      {/* Bulk Actions */}
      {selectedLeads.size > 0 && (
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm font-semibold text-dark-text-primary">
                {selectedLeads.size} lead{selectedLeads.size !== 1 ? 's' : ''} selected
              </span>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => setShowBulkAssignModal(true)}
                  variant="primary"
                  size="sm"
                >
                  <StoreIcon className="w-4 h-4" />
                  Assign to Store
                </Button>
                <Button
                  onClick={handleBulkDelete}
                  variant="danger"
                  size="sm"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Selected
                </Button>
                <Button
                  onClick={handleBulkMarkDNC}
                  variant="warning"
                  size="sm"
                >
                  Mark as DNC
                </Button>
              </div>
            </div>
            <button
              onClick={() => setSelectedLeads(new Set())}
              className="text-sm text-dark-text-muted hover:text-dark-text-primary transition-colors"
            >
              Clear Selection
            </button>
          </div>
        </Card>
      )}

      {/* Leads Table - Professional & Efficient */}
      <Card 
        title="All Leads" 
        subtitle={`${filteredLeads.length} leads found`} 
        className="w-full" 
        noPadding
        style={{ overflow: 'hidden', width: '100%', maxWidth: '100%' }}
      >
        {loading ? (
          <div className="space-y-3 p-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-16 bg-dark-elevated border border-dark-border rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 p-6">
            <div className="w-20 h-20 rounded-full bg-dark-elevated border-2 border-dark-border flex items-center justify-center mb-4 animate-bounce">
              <Users className="w-10 h-10 text-dark-text-muted" />
            </div>
            <p className="text-lg font-semibold text-dark-text-primary mb-2">
              No leads found
            </p>
            <p className="text-sm text-dark-text-muted mb-6">
              {searchTerm ? 'Try a different search term' : 'Add your first lead to get started'}
            </p>
            {!searchTerm && (
              <Button onClick={() => setShowAddModal(true)} variant="primary">
                <Plus className="w-4 h-4" />
                Add Lead
              </Button>
            )}
          </div>
        ) : (
          <div 
            className="table-scroll-container"
            style={{ 
              width: '100%',
              maxWidth: '100%',
              overflowX: 'auto',
              overflowY: 'visible',
              boxSizing: 'border-box'
            }}
          >
            <table 
              className="table-fixed" 
              style={{ 
                width: '1400px', 
                minWidth: '1400px', 
                tableLayout: 'fixed',
                margin: 0
              }}
            >
              <thead>
                <tr className="border-b-2 border-dark-border">
                  <th className="text-center py-3 px-4" style={{ width: '50px' }}>
                    <input
                      type="checkbox"
                      checked={selectedLeads.size === paginatedLeads.length && paginatedLeads.length > 0}
                      onChange={handleSelectAll}
                      className="w-4 h-4 text-primary bg-dark-elevated border-2 border-dark-border rounded focus:ring-primary focus:ring-2"
                    />
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('name')}
                    style={{ width: '180px' }}
                  >
                    <div className="flex items-center gap-2">
                      Name
                      <span className="text-primary-light">{getSortIcon('name')}</span>
                    </div>
                  </th>
                  <th 
                    className="text-left py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('phone_number')}
                    style={{ width: '150px' }}
                  >
                    <div className="flex items-center gap-2">
                      Phone
                      <span className="text-primary-light">{getSortIcon('phone_number')}</span>
                    </div>
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-dark-text-primary" style={{ width: '200px' }}>Address</th>
                  <th 
                    className="text-center py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('priority')}
                    style={{ width: '100px' }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      Priority
                      <span className="text-primary-light">{getSortIcon('priority')}</span>
                    </div>
                  </th>
                  <th 
                    className="text-center py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('call_count')}
                    style={{ width: '80px' }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      Calls
                      <span className="text-primary-light">{getSortIcon('call_count')}</span>
                    </div>
                  </th>
                  <th 
                    className="text-center py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('dnc_flag')}
                    style={{ width: '120px' }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      Status
                      <span className="text-primary-light">{getSortIcon('dnc_flag')}</span>
                      {sortField === 'dnc_flag' && (
                        <span className="text-xs text-dark-text-muted">
                          ({sortDirection === 'asc' ? 'Active first' : 'DNC first'})
                        </span>
                      )}
                    </div>
                  </th>
                  <th 
                    className="text-center py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('store_id')}
                    style={{ width: '120px' }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      Store
                      <span className="text-primary-light">{getSortIcon('store_id')}</span>
                    </div>
                  </th>
                  <th 
                    className="text-center py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('sms_verified')}
                    style={{ width: '130px' }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      SMS Consent
                      <span className="text-primary-light">{getSortIcon('sms_verified')}</span>
                    </div>
                  </th>
                  <th 
                    className="text-center py-3 px-4 font-semibold text-dark-text-primary cursor-pointer hover:bg-dark-elevated/30 transition-colors select-none"
                    onClick={() => handleSort('last_called')}
                    style={{ width: '120px' }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      Last Called
                      <span className="text-primary-light">{getSortIcon('last_called')}</span>
                    </div>
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-dark-text-primary" style={{ width: '100px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedLeads.map((lead) => (
                  <tr
                key={lead.lead_id}
                    className="group border-b border-dark-border hover:bg-dark-elevated/50 transition-colors duration-200"
                  >
                    {/* Checkbox */}
                    <td className="py-4 px-4 text-center">
                      <input
                        type="checkbox"
                        checked={selectedLeads.has(lead.lead_id)}
                        onChange={() => handleSelectLead(lead.lead_id)}
                        className="w-4 h-4 text-primary bg-dark-elevated border-2 border-dark-border rounded focus:ring-primary focus:ring-2"
                      />
                    </td>

                    {/* Name */}
                    <td className="py-4 px-4">
                      <div className="font-semibold text-dark-text-primary truncate max-w-[200px]">
                        {lead.name || 'Unknown'}
                      </div>
                    </td>

                    {/* Phone */}
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <Phone className="w-4 h-4 text-dark-text-muted flex-shrink-0" />
                        <span className="font-mono text-sm text-dark-text-secondary">
                          {lead.phone_number}
                        </span>
                      </div>
                    </td>

                    {/* Address */}
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-dark-text-muted flex-shrink-0" />
                        <span className="text-sm text-dark-text-secondary truncate max-w-[250px]">
                          {[lead.Address, lead.City, lead.State].filter(Boolean).join(', ') || 'No address'}
                        </span>
                      </div>
                    </td>

                    {/* Priority */}
                    <td className="py-4 px-4 text-center">
                      <Badge 
                        variant={lead.priority === 1 ? 'success' : lead.priority === 2 ? 'warning' : 'error'} 
                        size="sm"
                      >
                        {lead.priority || 1}
                      </Badge>
                    </td>

                    {/* Call Count */}
                    <td className="py-4 px-4 text-center">
                      <span className="text-sm font-semibold text-dark-text-primary">
                        {lead.call_count || 0}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-4 px-4 text-center">
                      {getDNCBadge(lead.dnc_flag)}
                    </td>

                    {/* Store (Milestone 12) */}
                    <td className="py-4 px-4 text-center">
                      {getStoreBadge(lead.store_id)}
                    </td>

                    {/* Consent Status */}
                    <td className="py-4 px-4 text-center">
                      {getConsentBadge(lead)}
                    </td>

                    {/* Last Called */}
                    <td className="py-4 px-4 text-center">
                      <span className="text-xs text-dark-text-muted">
                        {lead.last_called ? new Date(lead.last_called).toLocaleDateString() : 'Never'}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-4 px-4 text-center">
                  <div className="relative">
                    <button
                      onClick={() => setActiveMenu(activeMenu === lead.lead_id ? null : lead.lead_id)}
                      className="dropdown-trigger p-2 rounded-lg hover:bg-dark-surface transition-colors"
                    >
                      <MoreVertical className="w-4 h-4 text-dark-text-muted" />
                    </button>
                    
                    {/* Dropdown Menu */}
                    {activeMenu === lead.lead_id && (
                      <div className="dropdown-menu absolute right-0 top-full mt-1 w-40 bg-dark-surface border-2 border-dark-border rounded-lg shadow-modern-xl z-50 animate-scale-in">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            console.log('✏️ Edit button clicked for lead:', lead.lead_id);
                            openEditModal(lead);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-dark-text-primary hover:bg-primary/10 hover:text-primary transition-colors rounded-t-lg"
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            console.log('🗑️ Delete button clicked for lead:', lead.lead_id);
                            handleDeleteLead(lead.lead_id, lead.name || 'this lead');
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-danger hover:bg-danger/10 transition-colors rounded-b-lg"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-dark-border bg-dark-elevated/30">
                  <td className="py-3 px-4 text-center font-semibold text-dark-text-primary">
                    <div className="flex items-center justify-center gap-2">
                      <Users className="w-4 h-4" />
                      {selectedLeads.size > 0 ? `${selectedLeads.size} selected` : 'Select'}
                </div>
                  </td>
                  <td className="py-3 px-4 font-semibold text-dark-text-primary">
                    Total: {filteredLeads.length}
                  </td>
                  <td className="py-3 px-4 text-center font-semibold text-dark-text-primary">
                    {filteredLeads.filter(l => !l.dnc_flag).length} Active
                  </td>
                  <td className="py-3 px-4 text-center font-semibold text-dark-text-primary">
                    {filteredLeads.filter(l => l.dnc_flag).length} DNC
                  </td>
                  <td className="py-3 px-4 text-center font-semibold text-dark-text-primary">
                    {filteredLeads.filter(l => l.sms_verified).length} Verified
                  </td>
                  <td className="py-3 px-4 text-center font-semibold text-dark-text-primary">
                    {filteredLeads.filter(l => !l.sms_verified).length} Pending Consent
                  </td>
                  <td className="py-3 px-4 text-center font-semibold text-dark-text-primary">
                    {filteredLeads.reduce((sum, l) => sum + (l.call_count || 0), 0)} Total Calls
                  </td>
                  <td className="py-3 px-4 text-center font-semibold text-dark-text-primary">
                    {filteredLeads.length > 0 ? Math.round(filteredLeads.reduce((sum, l) => sum + (l.call_count || 0), 0) / filteredLeads.length * 100) / 100 : 0} Avg
                  </td>
                  <td colSpan={3} className="py-3 px-4 text-center text-sm text-dark-text-muted">
                    Showing {startIndex + 1}-{Math.min(endIndex, filteredLeads.length)} of {filteredLeads.length} leads
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Card>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm text-dark-text-muted">
                Show {itemsPerPage} per page
                    </span>
              <select
                value={itemsPerPage}
                onChange={(e) => {
                  setItemsPerPage(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="px-3 py-1 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
                  </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary text-sm hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                First
              </button>
              <button
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary text-sm hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pageNum = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                  if (pageNum > totalPages) return null;
                  
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-2 rounded-lg text-sm font-semibold transition-colors ${
                        currentPage === pageNum
                          ? 'bg-primary text-white'
                          : 'bg-dark-elevated border-2 border-dark-border text-dark-text-primary hover:border-primary/30'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                    </div>
              
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary text-sm hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="px-3 py-2 bg-dark-elevated border-2 border-dark-border rounded-lg text-dark-text-primary text-sm hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Last
              </button>
                </div>

            <span className="text-sm text-dark-text-muted">
              Page {currentPage} of {totalPages}
            </span>
              </div>
      </Card>
      )}

      {/* Add Lead Modal - Clean & Simple */}
      {showAddModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setShowAddModal(false)}
        >
          <div 
            className="w-full max-w-md h-[90vh] bg-dark-surface border-2 border-dark-border rounded-2xl shadow-modern-xl animate-scale-in flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-dark-border flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Plus className="w-5 h-5 text-primary-light" />
                </div>
                <h2 className="text-xl font-bold text-dark-text-primary">Add New Lead</h2>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body - Scrollable */}
            <div className="flex-1 overflow-y-auto">
            <form onSubmit={handleAddLead} className="p-6 space-y-5">
              {/* Phone */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Phone Number *
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                  <input
                    type="tel"
                    required
                    value={newLead.phone_number}
                    onChange={(e) => setNewLead({ ...newLead, phone_number: e.target.value })}
                    placeholder="+1234567890"
                    className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  />
                </div>
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={newLead.name}
                  onChange={(e) => setNewLead({ ...newLead, name: e.target.value })}
                  placeholder="John Doe"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* Address */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Address
                </label>
                <input
                  type="text"
                  value={newLead.Address || ''}
                  onChange={(e) => setNewLead({ ...newLead, Address: e.target.value })}
                  placeholder="123 Main Street"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* City */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  City
                </label>
                <input
                  type="text"
                  value={newLead.City || ''}
                  onChange={(e) => setNewLead({ ...newLead, City: e.target.value })}
                  placeholder="New York"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* County */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  County
                </label>
                <input
                  type="text"
                  value={newLead.County || ''}
                  onChange={(e) => setNewLead({ ...newLead, County: e.target.value })}
                  placeholder="Kings County"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* State */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  State
                </label>
                <input
                  type="text"
                  value={newLead.State || ''}
                  onChange={(e) => setNewLead({ ...newLead, State: e.target.value })}
                  placeholder="NY"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* Zip */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Zip Code
                </label>
                <input
                  type="text"
                  value={newLead.Zip || ''}
                  onChange={(e) => setNewLead({ ...newLead, Zip: e.target.value })}
                  placeholder="10001"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* Priority */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-3">
                  Priority: {newLead.priority}
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={newLead.priority}
                  onChange={(e) => setNewLead({ ...newLead, priority: Number(e.target.value) })}
                  className="w-full h-2 bg-dark-elevated rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-gradient-to-r [&::-webkit-slider-thumb]:from-primary [&::-webkit-slider-thumb]:to-primary-dark [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-all [&::-webkit-slider-thumb]:hover:scale-125 [&::-webkit-slider-thumb]:shadow-glow-primary"
                />
                <div className="flex justify-between mt-2">
                  {[1, 2, 3, 4, 5].map((p) => (
                    <span
                      key={p}
                      className={`text-xs font-semibold ${
                        p === newLead.priority ? 'text-primary-light' : 'text-dark-text-muted'
                      }`}
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            </form>
            </div>

            {/* Modal Footer - Fixed */}
            <div className="p-6 border-t border-dark-border flex-shrink-0">
              <div className="flex gap-3">
                <Button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  variant="secondary"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button 
                  type="button"
                  onClick={handleAddLead}
                  variant="primary" 
                  className="flex-1"
                >
                  <Plus className="w-4 h-4" />
                  Add Lead
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Lead Modal */}
      {showEditModal && editingLead && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setShowEditModal(false)}
        >
          <div 
            className="w-full max-w-md h-[90vh] bg-dark-surface border-2 border-dark-border rounded-2xl shadow-modern-xl animate-scale-in flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-dark-border flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-info/10 flex items-center justify-center">
                  <Edit className="w-5 h-5 text-info-light" />
                </div>
                <h2 className="text-xl font-bold text-dark-text-primary">Edit Lead</h2>
              </div>
              <button
                onClick={() => setShowEditModal(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body - Scrollable */}
            <div className="flex-1 overflow-y-auto">
            <form onSubmit={handleEditLead} className="p-6 space-y-5">
              {/* Phone */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Phone Number *
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-text-muted" />
                  <input
                    type="tel"
                    required
                    value={editingLead.phone_number}
                    onChange={(e) => setEditingLead({ ...editingLead, phone_number: e.target.value })}
                    placeholder="+1234567890"
                    className="w-full pl-11 pr-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                  />
                </div>
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={editingLead.name || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, name: e.target.value })}
                  placeholder="John Doe"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* Address */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Address
                </label>
                <input
                  type="text"
                  value={editingLead.Address || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, Address: e.target.value })}
                  placeholder="123 Main Street"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* City */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  City
                </label>
                <input
                  type="text"
                  value={editingLead.City || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, City: e.target.value })}
                  placeholder="New York"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* County */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  County
                </label>
                <input
                  type="text"
                  value={editingLead.County || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, County: e.target.value })}
                  placeholder="Kings County"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* State */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  State
                </label>
                <input
                  type="text"
                  value={editingLead.State || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, State: e.target.value })}
                  placeholder="NY"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* Zip */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-2">
                  Zip Code
                </label>
                <input
                  type="text"
                  value={editingLead.Zip || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, Zip: e.target.value })}
                  placeholder="10001"
                  className="w-full px-4 py-3 bg-dark-elevated border-2 border-dark-border hover:border-primary/30 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-lg text-dark-text-primary placeholder-dark-text-muted font-medium transition-all outline-none"
                />
              </div>

              {/* Priority */}
              <div>
                <label className="block text-sm font-semibold text-dark-text-primary mb-3">
                  Priority: {editingLead.priority}
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={editingLead.priority}
                  onChange={(e) => setEditingLead({ ...editingLead, priority: Number(e.target.value) })}
                  className="w-full h-2 bg-dark-elevated rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-gradient-to-r [&::-webkit-slider-thumb]:from-primary [&::-webkit-slider-thumb]:to-primary-dark [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-all [&::-webkit-slider-thumb]:hover:scale-125 [&::-webkit-slider-thumb]:shadow-glow-primary"
                />
                <div className="flex justify-between mt-2">
                  {[1, 2, 3, 4, 5].map((p) => (
                    <span
                      key={p}
                      className={`text-xs font-semibold ${
                        p === editingLead.priority ? 'text-primary-light' : 'text-dark-text-muted'
                      }`}
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            </form>
            </div>

            {/* Modal Footer - Fixed */}
            <div className="p-6 border-t border-dark-border flex-shrink-0">
              <div className="flex gap-3">
                <Button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  variant="secondary"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button 
                  type="button"
                  onClick={handleEditLead}
                  variant="primary" 
                  className="flex-1"
                >
                  <Edit className="w-4 h-4" />
                  Update Lead
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CSV Import Preview Modal */}
      {showImportModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setShowImportModal(false)}
        >
          <div 
            className="w-full max-w-4xl h-[90vh] bg-dark-surface border-2 border-dark-border rounded-2xl shadow-modern-xl animate-scale-in flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-dark-border flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-success-light" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-dark-text-primary">Import CSV Preview</h2>
                  <p className="text-sm text-dark-text-secondary">
                    {importPreview.length} leads ready to import
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowImportModal(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body - Scrollable */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                {importPreview.slice(0, 10).map((lead, index) => (
                  <div key={index} className="bg-dark-elevated border border-dark-border rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-dark-text-primary">{lead.name}</h3>
                        <p className="text-sm text-dark-text-secondary">
                          {lead.phone_number} • {[lead.Address, lead.City, lead.State].filter(Boolean).join(', ')}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {lead.dnc_flag && (
                          <Badge variant="neutral" size="sm">DNC</Badge>
                        )}
                        <Badge variant="success" size="sm">Ready</Badge>
                      </div>
                    </div>
                  </div>
                ))}
                {importPreview.length > 10 && (
                  <div className="text-center text-dark-text-muted text-sm">
                    ... and {importPreview.length - 10} more leads
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer - Fixed */}
            <div className="p-6 border-t border-dark-border flex-shrink-0">
              <div className="flex gap-3">
                <Button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  variant="secondary"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button 
                  type="button"
                  onClick={handleCSVImport}
                  variant="primary" 
                  className="flex-1"
                  disabled={importing}
                >
                  {importing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Importing...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Import {importPreview.length} Leads
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Assign to Store Modal (Milestone 12) */}
      {showBulkAssignModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setShowBulkAssignModal(false)}
        >
          <div 
            className="w-full max-w-md bg-dark-surface border-2 border-dark-border rounded-2xl shadow-modern-xl animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-dark-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Users className="w-5 h-5 text-primary-light" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-dark-text-primary">Assign to Store</h2>
                  <p className="text-sm text-dark-text-secondary">
                    {selectedLeads.size} leads selected
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowBulkAssignModal(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              <div className="space-y-4">
                <div className="bg-info/10 border border-info/30 rounded-lg p-4">
                  <p className="text-sm text-dark-text-primary">
                    ⚠️ <strong>Important:</strong> No SMS will be sent during this assignment. 
                    Leads will only be assigned to the selected store.
                  </p>
                </div>

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
                        {bulkAssignStoreId ? (
                          <>
                            <StoreIcon className="absolute left-4 w-4 h-4 text-primary-light" />
                            <span className="truncate">
                              {stores.find(s => s.store_id === bulkAssignStoreId)?.name || 'Select store...'}
                            </span>
                            <span className="text-xs text-dark-text-muted truncate">
                              ({stores.find(s => s.store_id === bulkAssignStoreId)?.location})
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
                        {stores.map((store) => (
                          <button
                            key={store.store_id}
                            type="button"
                            onClick={() => {
                              setBulkAssignStoreId(store.store_id);
                              setIsAssignDropdownOpen(false);
                            }}
                            className={`w-full px-4 py-3 text-left hover:bg-primary/10 transition-colors flex items-center justify-between ${
                              bulkAssignStoreId === store.store_id ? 'bg-primary/5 border-l-2 border-primary-light' : ''
                            }`}
                          >
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-dark-text-primary">{store.name}</div>
                              <div className="text-xs text-dark-text-muted truncate">{store.location}</div>
                            </div>
                            {bulkAssignStoreId === store.store_id && <Check className="w-4 h-4 text-primary-light" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-dark-border">
              <div className="flex gap-3">
                <Button
                  type="button"
                  onClick={() => setShowBulkAssignModal(false)}
                  variant="secondary"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button 
                  type="button"
                  onClick={handleBulkAssignToStore}
                  variant="primary" 
                  className="flex-1"
                  disabled={!bulkAssignStoreId}
                >
                  <Users className="w-4 h-4" />
                  Assign {selectedLeads.size} Leads
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Auto-Assign Modal */}
      {showAutoAssignModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setShowAutoAssignModal(false)}
        >
          <div
            className="w-full max-w-md bg-dark-surface border-2 border-dark-border rounded-2xl shadow-modern-xl animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-6 border-b border-dark-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-primary-light" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-dark-text-primary">Auto-Assign Leads</h2>
                  <p className="text-sm text-dark-text-secondary">
                    Assign unassigned leads to stores by location
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowAutoAssignModal(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-dark-text-muted hover:text-dark-text-primary hover:bg-dark-elevated transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              <div className="space-y-4">
                <div className="bg-info/10 border border-info/30 rounded-lg p-4">
                  <p className="text-sm text-dark-text-primary">
                    <strong>How it works:</strong>
                  </p>
                  <ul className="text-sm text-dark-text-muted mt-2 space-y-1 list-disc list-inside">
                    <li>Matches leads to stores by City, State, or County</li>
                    <li>Distributes leads evenly across matching stores</li>
                    <li>Only processes unassigned leads (store_id IS NULL)</li>
                    <li>Leads without location data will be skipped</li>
                  </ul>
                </div>

                <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
                  <p className="text-sm text-dark-text-primary">
                    ⚠️ <strong>Note:</strong> This will assign ALL unassigned leads. No SMS will be sent during assignment.
                  </p>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-dark-border flex gap-3">
              <Button
                onClick={() => setShowAutoAssignModal(false)}
                variant="secondary"
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleAutoAssign}
                variant="primary"
                className="flex-1"
                disabled={loading}
              >
                <Sparkles className="w-4 h-4" />
                Auto-Assign Now
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadsPage;
