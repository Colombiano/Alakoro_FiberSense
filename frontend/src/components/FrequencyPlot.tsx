"""
Alakoro FiberSense - Frequency Plot
Plot de analise espectral (FFT).
"""
import React, { useRef, useEffect } from 'react';

interface FrequencyPlotProps {
  data: { frequencies: number[]; magnitude: number[] } | null;
}

const FrequencyPlot: React.FC<FrequencyPlotProps> = ({ data }) => {
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
    const maxFreq = Math.max(...data.frequencies, 1);
    const maxMag = Math.max(...data.magnitude, 1);

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

    // Draw spectrum
    ctx.strokeStyle = '#0ea5e9';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < data.frequencies.length; i++) {
      const x = padding.left + (data.frequencies[i] / maxFreq) * plotWidth;
      const y = padding.top + plotHeight - (data.magnitude[i] / maxMag) * plotHeight;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Fill area
    ctx.fillStyle = 'rgba(14, 165, 233, 0.1)';
    ctx.lineTo(padding.left + plotWidth, padding.top + plotHeight);
    ctx.lineTo(padding.left, padding.top + plotHeight);
    ctx.closePath();
    ctx.fill();

    // Labels
    ctx.fillStyle = '#9ca3af';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    for (let i = 0; i <= 5; i++) {
      const freq = (i / 5) * maxFreq;
      const x = padding.left + (i / 5) * plotWidth;
      ctx.fillText(`${freq.toFixed(0)} Hz`, x, height - 10);
    }

    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
      const mag = (i / 5) * maxMag;
      const y = padding.top + plotHeight - (i / 5) * plotHeight;
      ctx.fillText(mag.toFixed(2), padding.left - 10, y + 4);
    }

    ctx.save();
    ctx.translate(15, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText('Magnitude', 0, 0);
    ctx.restore();

  }, [data]);

  if (!data) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-500">
        Sem dados de frequencia
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

export default FrequencyPlot;
