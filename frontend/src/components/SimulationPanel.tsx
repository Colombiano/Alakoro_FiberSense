"""
Alakoro FiberSense - Simulation Panel
Painel de simulacao com configuracao de eventos.
"""
import React, { useState } from 'react';
import { SignalType, SimulationConfig } from '../types';

interface SimulationPanelProps {
  signalType: SignalType;
  onSimulationComplete: (data: any) => void;
  onStatusChange: (processing: boolean) => void;
}

const SimulationPanel: React.FC<SimulationPanelProps> = ({
  signalType,
  onSimulationComplete,
  onStatusChange,
}) => {
  const [config, setConfig] = useState<SimulationConfig>({
    fiberLength: 10000,
    spatialResolution: 1,
    samplingRate: signalType === 'das' ? 1000 : signalType === 'dts' ? 1 : 100,
    duration: signalType === 'das' ? 10 : 3600,
    noiseLevel: 0.01,
    events: [],
  });

  const [eventForm, setEventForm] = useState({
    position: 5000,
    amplitude: 1.0,
    frequency: 50,
    width: 100,
    type: 'gaussian',
  });

  const addEvent = () => {
    setConfig(prev => ({
      ...prev,
      events: [...prev.events, { ...eventForm }],
    }));
  };

  const removeEvent = (index: number) => {
    setConfig(prev => ({
      ...prev,
      events: prev.events.filter((_, i) => i !== index),
    }));
  };

  const runSimulation = async () => {
    onStatusChange(true);
    try {
      const response = await fetch(`/api/simulation/${signalType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await response.json();
      onSimulationComplete(data);
    } catch (error) {
      console.error('Simulation error:', error);
    } finally {
      onStatusChange(false);
    }
  };

  return (
    <div className="glass-panel p-4">
      <h3 className="text-lg font-semibold text-white mb-4">Simulacao</h3>

      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Comprimento (m)</label>
          <input
            type="number"
            value={config.fiberLength}
            onChange={(e) => setConfig(prev => ({ ...prev, fiberLength: Number(e.target.value) }))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Resolucao (m)</label>
          <input
            type="number"
            value={config.spatialResolution}
            onChange={(e) => setConfig(prev => ({ ...prev, spatialResolution: Number(e.target.value) }))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white"
            step={0.1}
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Taxa (Hz)</label>
          <input
            type="number"
            value={config.samplingRate}
            onChange={(e) => setConfig(prev => ({ ...prev, samplingRate: Number(e.target.value) }))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Duracao (s)</label>
          <input
            type="number"
            value={config.duration}
            onChange={(e) => setConfig(prev => ({ ...prev, duration: Number(e.target.value) }))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Ruido</label>
          <input
            type="number"
            value={config.noiseLevel}
            onChange={(e) => setConfig(prev => ({ ...prev, noiseLevel: Number(e.target.value) }))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white"
            step={0.001}
          />
        </div>

        {/* Events */}
        <div className="pt-2 border-t border-gray-700">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Eventos ({config.events.length})</h4>

          <div className="space-y-2 max-h-32 overflow-y-auto">
            {config.events.map((evt, idx) => (
              <div key={idx} className="flex items-center justify-between bg-gray-700/50 rounded px-2 py-1">
                <span className="text-xs text-gray-300">
                  {evt.type} @ {evt.position}m
                </span>
                <button
                  onClick={() => removeEvent(idx)}
                  className="text-red-400 hover:text-red-300 text-xs"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="mt-2 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                placeholder="Pos (m)"
                value={eventForm.position}
                onChange={(e) => setEventForm(prev => ({ ...prev, position: Number(e.target.value) }))}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white"
              />
              <input
                type="number"
                placeholder="Amp"
                value={eventForm.amplitude}
                onChange={(e) => setEventForm(prev => ({ ...prev, amplitude: Number(e.target.value) }))}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white"
                step={0.1}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={eventForm.type}
                onChange={(e) => setEventForm(prev => ({ ...prev, type: e.target.value }))}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white"
              >
                <option value="gaussian">Gaussiano</option>
                <option value="exponential">Exponencial</option>
                <option value="boxcar">Boxcar</option>
              </select>
              <button
                onClick={addEvent}
                className="btn-secondary text-xs py-1"
              >
                + Adicionar
              </button>
            </div>
          </div>
        </div>

        <button
          onClick={runSimulation}
          className="w-full btn-primary mt-2"
        >
          Executar Simulacao
        </button>
      </div>
    </div>
  );
};

export default SimulationPanel;
