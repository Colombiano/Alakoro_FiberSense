"""
Alakoro FiberSense - Status Bar
Barra de status com informacoes do sistema.
"""
import React from 'react';
import { StatusInfo } from '../types';

interface StatusBarProps {
  status: StatusInfo;
}

const StatusBar: React.FC<StatusBarProps> = ({ status }) => {
  return (
    <div className="flex items-center gap-4 text-sm">
      {/* Connection */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${status.connected ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className={status.connected ? 'text-green-400' : 'text-red-400'}>
          {status.connected ? 'Conectado' : 'Desconectado'}
        </span>
      </div>

      {/* Processing */}
      {status.processing && (
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
          <span className="text-yellow-400">Processando...</span>
        </div>
      )}

      {/* Signal Type */}
      <div className="text-gray-400">
        <span className="text-gray-500">Tipo:</span>{' '}
        <span className="text-white uppercase">{status.signalType}</span>
      </div>

      {/* Memory */}
      <div className="text-gray-400">
        <span className="text-gray-500">Mem:</span>{' '}
        <span className="text-white">{status.memory} MB</span>
      </div>

      {/* CPU */}
      <div className="text-gray-400">
        <span className="text-gray-500">CPU:</span>{' '}
        <span className="text-white">{status.cpu}%</span>
      </div>
    </div>
  );
};

export default StatusBar;
