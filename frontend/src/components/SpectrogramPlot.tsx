"""
Alakoro FiberSense - Spectrogram Plot
Plot de espectrograma usando Canvas API.
"""
import React, { useRef, useEffect } from 'react';

interface SpectrogramPlotProps {
  data: {
    frequencies: number[];
    times: number[];
    spectrogram: number[][];
  } | null;
}

const SpectrogramPlot: React.FC<SpectrogramPlotProps> = ({ data }) => {
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

    // Find min/max for normalization
    let minVal = Infinity;
    let maxVal = -Infinity;
    for (const row of data.spectrogram) {
      for (const val of row) {
        if (val < minVal) minVal = val;
        if (val > maxVal) maxVal = val;
      }
    }
    const range = maxVal - minVal || 1;

    // Draw spectrogram
    const nTimes = data.times.length;
    const nFreqs = data.frequencies.length;
    const cellWidth = plotWidth / nTimes;
    const cellHeight = plotHeight / nFreqs;

    for (let t = 0; t < nTimes; t++) {
      for (let f = 0; f < nFreqs; f++) {
        const val = data.spectrogram[t]?.[f] || minVal;
        const normalized = (val - minVal) / range;

        // HSL colormap: blue (240) to red (0)
        const hue = (1 - normalized) * 240;
        const lightness = 20 + normalized * 40;
        ctx.fillStyle = `hsl(${hue}, 100%, ${lightness}%)`;

        const x = padding.left + t * cellWidth;
        const y = padding.top + (nFreqs - 1 - f) * cellHeight;
        ctx.fillRect(x, y, cellWidth + 0.5, cellHeight + 0.5);
      }
    }

    // Labels
    ctx.fillStyle = '#9ca3af';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';

    // Time labels
    const nTimeLabels = 5;
    for (let i = 0; i <= nTimeLabels; i++) {
      const idx = Math.floor((i / nTimeLabels) * (nTimes - 1));
      const x = padding.left + (i / nTimeLabels) * plotWidth;
      ctx.fillText(`${data.times[idx].toFixed(2)}s`, x, height - 10);
    }

    // Frequency labels
    ctx.textAlign = 'right';
    const nFreqLabels = 5;
    for (let i = 0; i <= nFreqLabels; i++) {
      const idx = Math.floor((i / nFreqLabels) * (nFreqs - 1));
      const y = padding.top + plotHeight - (i / nFreqLabels) * plotHeight;
      ctx.fillText(`${data.frequencies[idx].toFixed(0)}Hz`, padding.left - 10, y + 4);
    }

    // Axis labels
    ctx.save();
    ctx.translate(15, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText('Frequencia (Hz)', 0, 0);
    ctx.restore();

    ctx.textAlign = 'center';
    ctx.fillText('Tempo (s)', width / 2, height - 2);

  }, [data]);

  if (!data) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-500">
        Sem dados de espectrograma
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

export default SpectrogramPlot;
