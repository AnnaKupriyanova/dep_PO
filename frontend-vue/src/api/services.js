// Без axios - используем нативный fetch API

const API_BASE = '/discovery';

export const discoveryService = {
  async getServices(tag) {
    const url = tag ? `${API_BASE}/services?tag=${tag}` : `${API_BASE}/services`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Failed to fetch services: ${response.status}`);
    return response.json();
  },

  async getStats() {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error(`Failed to fetch stats: ${response.status}`);
    return response.json();
  },

  async healthCheck() {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
    return response.json();
  },

  async registerService(service) {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(service)
    });
    if (!response.ok) throw new Error(`Failed to register service: ${response.status}`);
    return response.json();
  }
};