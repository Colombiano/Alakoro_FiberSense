"""
Alakoro FiberSense - Profile Plot
Plot de perfil espacial do sinal.
"""
import React, { useRef, useEffect } from 'react';
import { SignalType } from '../types';

interface ProfilePlotProps {
  data: { distance: number[]; amplitude: number[] } | null;
  signalType: SignalType;
}

const ProfilePlot: React.FC<ProfilePlotProps> = ({ data, signalType }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const padding = { top: 20, right: 20, bottom: 40, left: 60 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;

    // Clear
    ctx.fillStyle = '#1f2937';
    ctx.fillRect(0, 0, width, height);

    // Find range
    const minDist = Math.min(...data.distance);
    const maxDist = Math.max(...data.distance);
    const minAmp = Math.min(...data.amplitude);
    const maxAmp = Math.max(...data.amplitude);
    const ampRange = maxAmp - minAmp || 1;

    // Color based on signal type
    const colors = {
      das: '#0ea5e9',
      dts: '#f97316',
      dss: '#22c55e',
    };

    // Draw grid
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 5; i++) {
      const x = padding.left + (i / 5) * plotWidth;
      const y = padding.top + (i / 5) * plotHeight;
      ctx.beginPath();
      ctx.moveTo(x, padding.top);
      ctx.lineTo(x, padding.top + plotHeight);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + plotWidth, y);
      ctx.stroke();
    }

    // Draw profile
    ctx.strokeStyle = colors[signalType];
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < data.distance.length; i++) {
      const x = padding.left + ((data.distance[i] - minDist) / (maxDist - minDist)) * plotWidth;
      const y = padding.top + plotHeight - ((data.amplitude[i] - minAmp) / ampRange) * plotHeight;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Labels
    ctx.fillStyle = '#9ca3af';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    for (let i = 0; i <= 5; i++) {
      const dist = minDist + (i / 5) * (maxDist - minDist);
      const x = padding.left + (i / 5) * plotWidth;
      ctx.fillText(`${(dist / 1000).toFixed(1)} km`, x, height - 10);
    }

    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
      const amp = minAmp + (i / 5) * ampRange;
      const y = padding.top + plotHeight - (i / 5) * plotHeight;
      ctx.fillText(amp.toFixed(3), padding.left - 10, y + 4);
    }

    ctx.save();
    ctx.translate(15, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText(
      signalType === 'dts' ? 'Temperatura (C)' : 
      signalType === 'dss' ? 'Strain' : 'Amplitude',
      0, 0
    );
    ctx.restore();

  }, [data, signalType]);

  if (!data) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-500">
        Sem dados de perfil
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-48 rounded"
      style={{ background: '#1f2937' }}
    />
  );
};

export default ProfilePlot;
