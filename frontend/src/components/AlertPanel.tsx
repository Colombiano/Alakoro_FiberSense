"""
Alakoro FiberSense - Alert Panel
Painel de alertas para o dashboard.
"""
import React from 'react';
import { Alert } from '../types';

interface AlertPanelProps {
  alerts: Alert[];
  onAcknowledge?: (id: string) => void;
  onClearAll?: () => void;
}

const AlertPanel: React.FC<AlertPanelProps> = ({ alerts, onAcknowledge, onClearAll }) => {
  const getLevelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bg-red-500/20 border-red-500 text-red-400';
      case 'warning': return 'bg-yellow-500/20 border-yellow-500 text-yellow-400';
      default: return 'bg-blue-500/20 border-blue-500 text-blue-400';
    }
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'critical': return '⚠';
      case 'warning': return '!';
      default: return 'ℹ';
    }
  };

  return (
    <div className="glass-panel p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Alertas</h3>
        <div className="flex gap-2">
          <span className="text-sm text-gray-400">
            {alerts.filter(a => !a.acknowledged).length} novos
          </span>
          {onClearAll && (
            <button onClick={onClearAll} className="text-xs text-gray-500 hover:text-white">
              Limpar
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {alerts.length === 0 && (
          <div className="text-gray-500 text-sm text-center py-4">
            Nenhum alerta
          </div>
        )}

        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`p-3 rounded-lg border ${getLevelColor(alert.level)} ${
              alert.acknowledged ? 'opacity-50' : ''
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="text-lg">{getLevelIcon(alert.level)}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{alert.message}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs opacity-70">
                    {new Date(alert.createdAt).toLocaleTimeString()}
                  </span>
                  <span className="text-xs uppercase opacity-50">{alert.signalType}</span>
                </div>
              </div>
              {!alert.acknowledged && onAcknowledge && (
                <button
                  onClick={() => onAcknowledge(alert.id)}
                  className="text-xs hover:underline"
                >
                  OK
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AlertPanel;
