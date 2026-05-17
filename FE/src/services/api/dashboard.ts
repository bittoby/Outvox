// Dashboard API Services
import axios from 'axios';
import { API_CONFIG } from '../config';
import type { CallStats } from '../../types/stats';

/**
 * Get today's call statistics for dashboard
 */
export async function getCallStats(): Promise<CallStats> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/analytics/stats/today`);
    return {
      total_calls: response.data.total_calls || 0,
      interested: response.data.interested || 0,
      not_interested: response.data.not_interested || 0,
      callback: response.data.callback || 0,
      dnc: response.data.dnc || 0,
      pending_leads: response.data.pending_leads || 0,
      numbers: response.data.numbers || [],
    };
  } catch (error) {
    console.error('Error fetching call stats:', error);
    return {
      total_calls: 0,
      interested: 0,
      not_interested: 0,
      callback: 0,
      dnc: 0,
      pending_leads: 0,
      numbers: [],
    };
  }
}

/**
 * Get store locations with lead counts
 */
export async function getStoreLocations(): Promise<any> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/analytics/store-locations`);
    
    // Check if response has the expected structure
    if (!response.data) {
      console.warn('No data in store locations response');
      return { locations: [] };
    }
    
    const stores = response.data.stores || response.data || [];
    
    if (!Array.isArray(stores)) {
      console.warn('Stores data is not an array:', stores);
      return { locations: [] };
    }
    
    console.log(`✅ Fetched ${stores.length} stores from API`);
    
    // Transform backend store data to match frontend expected format
    const locations = stores.map((store: any) => {
      // Get available/open days (default to Mon-Sun if not provided)
      const openDays = store.open_days || store.available_days || 'Mon-Fri';
      
      return {
        store_id: store.store_id,
        name: store.name || 'Unknown Store',
        address: store.location || 'Address not available',
        open_days: openDays,
        status: store.is_active ? 'open' : 'closed',
        calls_today: store.calls_today || 0,
        hours: '9:00 AM - 6:00 PM', // Default hours, can be updated if backend provides this
        total_leads: store.total_leads || 0,
        total_phone_numbers: store.total_phone_numbers || 0,
      };
    });
    
    return {
      locations: locations,
    };
  } catch (error: any) {
    console.error('Error fetching store locations:', error);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
    return {
      locations: [],
    };
  }
}

/**
 * Get lead priority statistics
 */
export async function getLeadPriorityStats(): Promise<any> {
  try {
    const response = await axios.get(`${API_CONFIG.DB_SERVICE}/api/analytics/stats/priority-stats`);
    return response.data || {
      high_priority: 0,
      medium_priority: 0,
      low_priority: 0,
      total: 0,
    };
  } catch (error) {
    console.error('Error fetching lead priority stats:', error);
    return {
      high_priority: 0,
      medium_priority: 0,
      low_priority: 0,
      total: 0,
    };
  }
}

export default {
  getCallStats,
  getStoreLocations,
  getLeadPriorityStats,
};

