"""
Alakoro FiberSense - Signal Store
Store reativo baseado em Proxy para estado global.
"""
import { SignalData, Alert, SignalType } from '../types';

interface StoreState {
  signals: SignalData[];
  alerts: Alert[];
  activeSignalType: SignalType;
  processing: boolean;
  connected: boolean;
}

const createStore = () => {
  const state: StoreState = {
    signals: [],
    alerts: [],
    activeSignalType: 'das',
    processing: false,
    connected: false,
  };

  const listeners = new Set<(state: StoreState) => void>();

  const proxy = new Proxy(state, {
    set(target, prop, value) {
      (target as any)[prop] = value;
      listeners.forEach((cb) => cb(target));
      return true;
    },
  });

  return {
    state: proxy,
    subscribe(callback: (state: StoreState) => void) {
      listeners.add(callback);
      return () => listeners.delete(callback);
    },
    addSignal(signal: SignalData) {
      proxy.signals = [...proxy.signals, signal];
    },
    addAlert(alert: Alert) {
      proxy.alerts = [...proxy.alerts, alert];
    },
    acknowledgeAlert(id: string) {
      proxy.alerts = proxy.alerts.map((a) =>
        a.id === id ? { ...a, acknowledged: true } : a
      );
    },
    clearAlerts() {
      proxy.alerts = [];
    },
  };
};

export const signalStore = createStore();
