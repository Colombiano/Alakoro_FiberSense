"""
Alakoro FiberSense - TypeScript Types
Tipos compartilhados entre frontend e backend.
"""

export type SignalType = 'das' | 'dts' | 'dss';

export interface FiberParams {
  fiberLength: number;
  spatialResolution: number;
  samplingRate: number;
  gaugeLength: number;
  refractiveIndex: number;
  cableType: string;
}

export interface SignalData {
  id: string;
  signalType: SignalType;
  waterfall?: {
    matrix: number[][];
    distance: number[];
    time: number[];
  };
  profile?: {
    distance: number[];
    amplitude: number[];
  };
  spectrogram?: {
    frequencies: number[];
    times: number[];
    spectrogram: number[][];
  };
  fft?: {
    frequencies: number[];
    magnitude: number[];
  };
  createdAt: string;
}

export interface SignalEvent {
  id: string;
  signalType: SignalType;
  eventType: string;
  position?: number;
  amplitude?: number;
  frequency?: number;
  confidence: number;
  timestamp: string;
}

export interface SignalAlert {
  id: string;
  signalType: SignalType;
  level: 'critical' | 'warning' | 'info';
  message: string;
  eventId?: string;
  acknowledged: boolean;
  createdAt: string;
}

export interface SignalConfig {
  signalType: SignalType;
  fiberLength: number;
  spatialResolution: number;
  samplingRate: number;
  colormap?: string;
  scale?: 'linear' | 'log';
  useCppEngine?: boolean;
}

export interface SimulationConfig {
  fiberLength: number;
  spatialResolution: number;
  samplingRate: number;
  duration: number;
  noiseLevel: number;
  events: SimulationEvent[];
}

export interface SimulationEvent {
  position: number;
  amplitude: number;
  frequency?: number;
  width: number;
  type: string;
  startTime?: number;
  duration?: number;
}

export interface ProcessingStatus {
  signalId: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  result?: any;
  error?: string;
}

export interface StatusInfo {
  connected: boolean;
  processing: boolean;
  signalType: SignalType;
  memory: number;
  cpu: number;
}
