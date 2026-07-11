"""
Alakoro FiberSense - Dashboard
Dashboard principal com tabs DAS/DTS/DSS.
"""
import React, { useState, useCallback } from 'react';
import { SignalType, SignalData, Alert, SignalConfig, SimulationConfig, StatusInfo } from '../types';
import { signalStore } from '../lib/signalStore';
import WaterfallPlot from './WaterfallPlot';
import SpectrogramPlot from './SpectrogramPlot';
import ProfilePlot from './ProfilePlot';
import FrequencyPlot from './FrequencyPlot';
import SimulationPanel from './SimulationPanel';
import ConfigPanel from './ConfigPanel';
import StatusBar from './StatusBar';
import AlertPanel from './AlertPanel';

const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SignalType>('das');
  const [signalData, setSignalData] = useState<SignalData | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [status, setStatus] = useState<StatusInfo>({
    connected: true,
    processing: false,
    signalType: 'das',
    memory: 0,
    cpu: 0,
  });
  const [config, setConfig] = useState<SignalConfig>({
    signalType: 'das',
    fiberLength: 10000,
    spatialResolution: 1,
    samplingRate: 1000,
    colormap: 'viridis',
    scale: 'linear',
    useCppEngine: true,
  });

  const tabs: { id: SignalType; label: string }[] = [
    { id: 'das', label: 'DAS' },
    { id: 'dts', label: 'DTS' },
    { id: 'dss', label: 'DSS' },
  ];

  const handleSimulationComplete = useCallback((data: SignalData) => {
    setSignalData(data);
    setStatus(prev => ({ ...prev, processing: false }));
  }, []);

  const handleAcknowledgeAlert = useCallback((id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
  }, []);

  const handleClearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Alakoro FiberSense</h1>
            <p className="text-sm text-gray-400">Sistema de Processamento de Fibra Otica Distribuida</p>
          </div>
          <StatusBar status={status} />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mt-4">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setConfig(prev => ({ ...prev, signalType: tab.id }));
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Left Sidebar - Config */}
          <div className="col-span-3 space-y-4">
            <ConfigPanel config={config} onChange={setConfig} />
            <SimulationPanel
              signalType={activeTab}
              onSimulationComplete={handleSimulationComplete}
              onStatusChange={(processing) => setStatus(prev => ({ ...prev, processing }))}
            />
          </div>

          {/* Center - Plots */}
          <div className="col-span-6 space-y-4">
            {/* Waterfall Plot */}
            <div className="glass-panel p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">
                Waterfall - {activeTab.toUpperCase()}
              </h3>
              <WaterfallPlot
                data={signalData?.waterfall || null}
                signalType={activeTab}
                colormap={config.colormap}
              />
            </div>

            {/* Profile Plot */}
            <div className="glass-panel p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Perfil Espacial</h3>
              <ProfilePlot
                data={signalData?.profile || null}
                signalType={activeTab}
              />
            </div>

            {/* Spectrogram */}
            <div className="glass-panel p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Espectrograma</h3>
              <SpectrogramPlot
                data={signalData?.spectrogram || null}
              />
            </div>

            {/* Frequency Plot */}
            <div className="glass-panel p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Analise Espectral</h3>
              <FrequencyPlot
                data={signalData?.fft || null}
              />
            </div>
          </div>

          {/* Right Sidebar - Alerts */}
          <div className="col-span-3">
            <AlertPanel
              alerts={alerts}
              onAcknowledge={handleAcknowledgeAlert}
              onClearAll={handleClearAlerts}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
