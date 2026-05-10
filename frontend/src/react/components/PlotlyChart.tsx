import React, { useEffect, useRef } from 'react';

interface PlotlyChartProps {
  data: any[];
  layout?: any;
  config?: any;
  style?: React.CSSProperties;
}

const defaultLayout = {
  template: 'plotly_dark',
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#c0c0d0' },
  margin: { l: 60, r: 20, t: 40, b: 40 },
};

function loadPlotly(): Promise<any> {
  return new Promise((resolve, reject) => {
    if ((window as any).Plotly) { resolve((window as any).Plotly); return; }
    const script = document.createElement('script');
    script.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
    script.onload = () => resolve((window as any).Plotly);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

const PlotlyChart: React.FC<PlotlyChartProps> = ({ data, layout, config, style }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;
    loadPlotly().then((Plotly: any) => {
      const l = { ...defaultLayout, ...layout };
      const c = { responsive: true, displaylogo: false, ...config };
      Plotly.newPlot(containerRef.current, data, l, c);
    }).catch(console.error);
  }, [data, layout, config]);

  return <div ref={containerRef} style={{ width: '100%', minHeight: '300px', ...style }} />;
};

export default PlotlyChart;
