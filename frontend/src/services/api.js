/**
 * CodeSentinel - API Client
 * Handles all backend communication.
 */

const API_BASE = '/api';

class ApiClient {
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health check
  async getHealth() {
    return this.request('/health');
  }

  // Create a new scan from GitHub URL
  async createScan(repoUrl) {
    return this.request('/scans', {
      method: 'POST',
      body: JSON.stringify({ repo_url: repoUrl }),
    });
  }

  // Create a new scan from ZIP upload
  async uploadScan(file, projectName = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (projectName) {
      formData.append('project_name', projectName);
    }

    const url = `${API_BASE}/scans/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Get scan details with issues
  async getScan(scanId) {
    return this.request(`/scans/${scanId}`);
  }

  // List all scans
  async listScans(limit = 20, offset = 0) {
    return this.request(`/scans?limit=${limit}&offset=${offset}`);
  }

  // Get scan progress (polling fallback)
  async getScanProgress(scanId) {
    return this.request(`/scans/${scanId}/progress`);
  }

  // Get report
  async getReport(scanId, format = 'json') {
    return this.request(`/scans/${scanId}/report?format=${format}`);
  }

  // Delete scan
  async deleteScan(scanId) {
    return this.request(`/scans/${scanId}`, { method: 'DELETE' });
  }

  // WebSocket connection for real-time updates
  connectWebSocket(scanId, onMessage, onClose) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/scan/${scanId}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('WebSocket parse error:', e);
      }
    };

    ws.onclose = () => {
      if (onClose) onClose();
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return ws;
  }
}

export const api = new ApiClient();
export default api;
