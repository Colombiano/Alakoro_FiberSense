"""
Alakoro FiberSense - Waterfall Plot
Heatmap waterfall para visualizacao de sinais DAS/DTS/DSS.
"""
import React, { useRef, useEffect } from 'react';
import { SignalType } from '../types';

interface WaterfallPlotProps {
  data: {
    matrix: number[][];
    distance: number[];
    time: number[];
  } | null;
  signalType: SignalType;
  colormap?: string;
}

const WaterfallPlot: React.FC<WaterfallPlotProps> = ({ data, signalType, colormap = 'viridis' }) => {
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

    // Find min/max
    let minVal = Infinity;
    let maxVal = -Infinity;
    for (const row of data.matrix) {
      for (const val of row) {
        if (val < minVal) minVal = val;
        if (val > maxVal) maxVal = val;
      }
    }
    const range = maxVal - minVal || 1;

    // Color maps
    const getColor = (normalized: number): string => {
      switch (colormap) {
        case 'inferno':
          return `hsl(${normalized * 30}, 100%, ${20 + normalized * 50}%)`;
        case 'plasma':
          return `hsl(${240 + normalized * 120}, 100%, ${30 + normalized * 40}%)`;
        case 'jet':
          return `hsl(${normalized * 280}, 100%, 50%)`;
        case 'hot':
          return `hsl(${normalized * 60}, 100%, ${30 + normalized * 40}%)`;
        default: // viridis
          return `hsl(${240 + normalized * 120}, 100%, ${25 + normalized * 45}%)`;
      }
    };

    // Type-specific color adjustments
    const getTypeColor = (normalized: number): string => {
      if (signalType === 'dts') {
        return `hsl(${10 + normalized * 40}, 100%, ${30 + normalized * 40}%)`; // orange
      } else if (signalType === 'dss') {
        return `hsl(${100 + normalized * 60}, 100%, ${30 + normalized * 40}%)`; // green
      }
      return getColor(normalized);
    };

    // Draw heatmap
    const nTime = data.matrix.length;
    const nDist = data.matrix[0]?.length || 0;
    const cellWidth = plotWidth / nDist;
    const cellHeight = plotHeight / nTime;

    for (let t = 0; t < nTime; t++) {
      for (let d = 0; d < nDist; d++) {
        const val = data.matrix[t]?.[d] || minVal;
        const normalized = Math.max(0, Math.min(1, (val - minVal) / range));
        ctx.fillStyle = getTypeColor(normalized);
        const x = padding.left + d * cellWidth;
        const y = padding.top + t * cellHeight;
        ctx.fillRect(x, y, cellWidth + 0.5, cellHeight + 0.5);
      }
    }

    // Labels
    ctx.fillStyle = '#9ca3af';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';

    // Distance labels
    const nDistLabels = 5;
    for (let i = 0; i <= nDistLabels; i++) {
      const idx = Math.floor((i / nDistLabels) * (nDist - 1));
      const x = padding.left + (i / nDistLabels) * plotWidth;
      const distKm = (data.distance[idx] / 1000).toFixed(1);
      ctx.fillText(`${distKm} km`, x, height - 10);
    }

    // Time labels
    ctx.textAlign = 'right';
    const nTimeLabels = 5;
    for (let i = 0; i <= nTimeLabels; i++) {
      const idx = Math.floor((i / nTimeLabels) * (nTime - 1));
      const y = padding.top + (i / nTimeLabels) * plotHeight;
      ctx.fillText(`${data.time[idx].toFixed(2)}s`, padding.left - 10, y + 4);
    }

    // Axis labels
    ctx.save();
    ctx.translate(15, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText('Tempo', 0, 0);
    ctx.restore();

    ctx.textAlign = 'center';
    ctx.fillText('Distancia (km)', width / 2, height - 2);

    // Legend
    const legendWidth = 100;
    const legendHeight = 10;
    const legendX = width - padding.right - legendWidth;
    const legendY = padding.top;

    for (let i = 0; i < legendWidth; i++) {
      const normalized = i / legendWidth;
      ctx.fillStyle = getTypeColor(normalized);
      ctx.fillRect(legendX + i, legendY, 1, legendHeight);
    }

    ctx.fillStyle = '#9ca3af';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${minVal.toFixed(2)}`, legendX, legendY + legendHeight + 12);
    ctx.fillText(`${maxVal.toFixed(2)}`, legendX + legendWidth, legendY + legendHeight + 12);

  }, [data, signalType, colormap]);

  if (!data) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        Execute uma simulacao para visualizar o waterfall
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-64 rounded"
      style={{ background: '#1f2937' }}
    />
  );
};

export default WaterfallPlot;
