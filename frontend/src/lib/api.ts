"""
Alakoro FiberSense - API Client
Cliente HTTP para a API do backend.
"""
import { SignalType } from '../types';

const API_BASE = '/api';

export const api = {
  // Upload
  uploadFile: async (file: File, signalType: SignalType, metadata?: Record<string, any>) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('signal_type', signalType);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await fetch(`${API_BASE}/upload/`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },

  // Simulation
  simulate: async (signalType: SignalType, config: Record<string, any>) => {
    const response = await fetch(`${API_BASE}/simulation/${signalType}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return response.json();
  },

  getSimulationTemplates: async () => {
    const response = await fetch(`${API_BASE}/simulation/templates`);
    return response.json();
  },

  // Processing
  processSignal: async (signalType: SignalType, signalId: string, config?: Record<string, any>) => {
    const response = await fetch(`${API_BASE}/${signalType}/process/${signalId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config || {}),
    });
    return response.json();
  },

  // Export
  exportSignal: async (signalId: string, format: 'hdf5' | 'csv' | 'netcdf') => {
    const response = await fetch(`${API_BASE}/export/${signalId}?format=${format}`);
    return response.blob();
  },

  // Health
  health: async () => {
    const response = await fetch(`${API_BASE}/health`);
    return response.json();
  },

  info: async () => {
    const response = await fetch(`${API_BASE}/info`);
    return response.json();
  },
};
