// CSV utility functions for lead import/export

export interface CSVLead {
  FirstName: string;
  LastName: string;
  Address: string;
  City: string;
  countyname: string;
  State: string;
  Zip: string;
  Phone: string;
  Phone_DNC: string;
  CellPhone: string;
  Cellphone_DNC: string;
  MIXPHONE: string;
  MIXPHONE_TYPE: string;
  MIXPHONE_DNC: string;
  DNC: string;
}

export interface LeadData {
  name: string;
  Address: string;
  City: string;
  County: string;
  State: string;
  Zip: string;
  phone_number: string;
  dnc_flag: boolean;
  priority: number;
}

/**
 * Parse CSV content and convert to LeadData format
 * Uses proper CSV parsing to handle commas, quotes, and special characters
 */
export function parseCSVToLeads(csvContent: string): LeadData[] {
  const lines = csvContent.split('\n').filter(line => line.trim());
  if (lines.length < 2) return [];

  const leads: LeadData[] = [];

  const clean = (value?: string) => {
    if (!value) return '';
    const trimmed = value.trim();
    // Remove surrounding quotes if present
    const unquoted = trimmed.replace(/^["']|["']$/g, '');
    return unquoted.toUpperCase() === 'NULL' ? '' : unquoted;
  };

  // Parse CSV with proper quote handling
  const parseCSVLine = (line: string): string[] => {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"') {
        // Handle escaped quotes ("")
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++; // Skip next quote
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    
    result.push(current.trim());
    return result;
  };

  const headers = parseCSVLine(lines[0]);

  for (let i = 1; i < lines.length; i++) {
    try {
      const values = parseCSVLine(lines[i]);
      if (values.length < headers.length) continue;

      const row: Record<string, string> = {};
      headers.forEach((header, index) => {
        row[header] = values[index] || '';
      });

      const firstName = clean(row.FirstName);
      const lastName = clean(row.LastName);
      const resPhone = clean(row.ResPhone);
      const busPhone = clean(row.BusPhone);
      const phone = resPhone || busPhone;

      if (!phone) continue;

      const lead: LeadData = {
        name: `${firstName} ${lastName}`.trim() || 'Unknown',
        Address: '',
        City: '',
        County: '',
        State: '',
        Zip: '',
        phone_number: phone,
        dnc_flag: false,
        priority: 1
      };

      leads.push(lead);
    } catch (error) {
      console.warn(`Failed to parse CSV line ${i + 1}:`, error);
      continue; // Skip invalid lines
    }
  }

  return leads;
}

/**
 * Convert LeadData array to CSV format
 */
export function exportLeadsToCSV(leads: LeadData[]): string {
  const headers = [
    'FirstName',
    'LastName', 
    'Address',
    'City',
    'countyname',
    'State',
    'Zip',
    'Phone',
    'Phone_DNC',
    'CellPhone',
    'Cellphone_DNC',
    'MIXPHONE',
    'MIXPHONE_TYPE',
    'MIXPHONE_DNC',
    'DNC'
  ];

  const csvRows = [headers.join(',')];

  leads.forEach(lead => {
    // Split name into first and last
    const nameParts = lead.name.split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';

    const row = [
      firstName,
      lastName,
      lead.Address || '',
      lead.City || '',
      lead.County || '',
      lead.State || '',
      lead.Zip || '',
      lead.phone_number, // Phone
      'N', // Phone_DNC
      '', // CellPhone
      'N', // Cellphone_DNC
      lead.phone_number, // MIXPHONE
      'W', // MIXPHONE_TYPE (W = Wireless)
      'N', // MIXPHONE_DNC
      lead.dnc_flag ? 'Y' : 'N' // DNC
    ];

    csvRows.push(row.join(','));
  });

  return csvRows.join('\n');
}

/**
 * Validate CSV file format
 * Supports both simple format (name,phone_number,...) and customer format (FirstName,LastName,ResPhone,...)
 */
export function validateCSVFormat(csvContent: string): { valid: boolean; error?: string } {
  const lines = csvContent.split('\n').filter(line => line.trim());
  
  if (lines.length < 2) {
    return { valid: false, error: 'CSV file must have at least a header row and one data row' };
  }

  const headers = lines[0].split(',').map(h => h.trim());
  
  // Check if it's simple format (name,phone_number,...)
  const hasSimpleFormat = headers.includes('phone_number');
  
  // Check if it's customer format (FirstName,LastName,ResPhone,...)
  const hasCustomerFormat = headers.includes('FirstName') || headers.includes('ResPhone');
  
  // Check if it has at least one phone field
  const hasPhoneField = headers.some(h => 
    h.toLowerCase().includes('phone') || 
    h.toLowerCase() === 'phone_number'
  );
  
  if (!hasSimpleFormat && !hasCustomerFormat && !hasPhoneField) {
    return { 
      valid: false, 
      error: 'CSV must include phone number field (phone_number, ResPhone, BusPhone, or Phone)' 
    };
  }

  return { valid: true };
}

/**
 * Download CSV file
 */
export function downloadCSV(csvContent: string, filename: string = 'leads.csv') {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

/**
 * Read file content as text
 */
export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string || '');
    reader.onerror = (e) => reject(e);
    reader.readAsText(file);
  });
}
