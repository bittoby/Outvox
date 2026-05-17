// API Configuration

export const API_CONFIG = {
  // Backend URLs
  DB_SERVICE: import.meta.env.VITE_DB_SERVICE_URL || 'http://localhost:8000',
  LOAD_BALANCER: import.meta.env.VITE_LOAD_BALANCER_URL || 'http://localhost:5100',
  
  // Individual agent URLs (for health checks)
  AGENT_URLS: Array.from({ length: 10 }, (_, i) => `http://localhost:${5101 + i}`),
  
  // Polling intervals (milliseconds) - kept for fallback
  POLLING: {
    DASHBOARD: 5000,      // 5 seconds (fallback if WebSocket fails)
    AGENT_STATUS: 3000,   // 3 seconds (fallback if WebSocket fails)
    CAMPAIGN: 2000,       // 2 seconds during active campaign (fallback)
  },
  
  // WebSocket configuration
  WEBSOCKET: {
    ENABLED: true,
    RECONNECT_DELAY: 1000,      // Initial reconnect delay (ms)
    MAX_RECONNECT_DELAY: 30000, // Max reconnect delay (ms)
    PING_INTERVAL: 30000,       // Ping interval (ms)
  },
};

export default API_CONFIG;

