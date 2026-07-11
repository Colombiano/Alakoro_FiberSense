"""
Alakoro FiberSense - Config Panel
Painel de configuracao do sistema.
"""
import React, { useState } from 'react';
import { SignalConfig } from '../types';

interface ConfigPanelProps {
  config: SignalConfig;
  onChange: (config: SignalConfig) => void;
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({ config, onChange }) => {
  const [localConfig, setLocalConfig] = useState<SignalConfig>(config);

  const handleChange = (field: keyof SignalConfig, value: any) => {
    const updated = { ...localConfig, [field]: value };
    setLocalConfig(updated);
    onChange(updated);
  };

  return (
    <div className="glass-panel p-4">
      <h3 className="text-lg font-semibold text-white mb-4">Configuracoes</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Tipo de Sinal</label>
          <select
            value={localConfig.signalType}
            onChange={(e) => handleChange('signalType', e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option value="das">DAS - Acustico</option>
            <option value="dts">DTS - Temperatura</option>
            <option value="dss">DSS - Deformacao</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Comprimento da Fibra (m)</label>
          <input
            type="number"
            value={localConfig.fiberLength}
            onChange={(e) => handleChange('fiberLength', Number(e.target.value))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            min={100}
            max={100000}
            step={100}
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Resolucao Espacial (m)</label>
          <input
            type="number"
            value={localConfig.spatialResolution}
            onChange={(e) => handleChange('spatialResolution', Number(e.target.value))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            min={0.1}
            max={10}
            step={0.1}
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Taxa de Amostragem (Hz)</label>
          <input
            type="number"
            value={localConfig.samplingRate}
            onChange={(e) => handleChange('samplingRate', Number(e.target.value))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            min={1}
            max={100000}
            step={100}
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Colormap</label>
          <select
            value={localConfig.colormap || 'viridis'}
            onChange={(e) => handleChange('colormap', e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option value="viridis">Viridis</option>
            <option value="inferno">Inferno</option>
            <option value="plasma">Plasma</option>
            <option value="jet">Jet</option>
            <option value="hot">Hot</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Escala</label>
          <select
            value={localConfig.scale || 'linear'}
            onChange={(e) => handleChange('scale', e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option value="linear">Linear</option>
            <option value="log">Logaritmica</option>
          </select>
        </div>

        <div className="pt-2 border-t border-gray-700">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={localConfig.useCppEngine || false}
              onChange={(e) => handleChange('useCppEngine', e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm text-gray-300">Usar Engine C++</span>
          </label>
        </div>
      </div>
    </div>
  );
};

export default ConfigPanel;
