import React, { useEffect, useRef } from 'react';

interface PlotlyChartProps {
  data?: any[];
  layout?: any;
  config?: any;
  chart?: any;
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

function getChartSpec(props: PlotlyChartProps) {
  if (props.chart && props.chart.data) {
    return {
      data: props.chart.data,
      layout: { ...defaultLayout, ...(props.chart.layout || {}) },
    };
  }
  if (props.data && props.data.length > 0) {
    return { data: props.data, layout: { ...defaultLayout, ...props.layout } };
  }
  return null;
}

const PlotlyChart: React.FC<PlotlyChartProps> = ({ data, layout, config, chart, style }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const spec = getChartSpec({ data, layout, config, chart });
    if (!spec) return;

    loadPlotly().then((Plotly: any) => {
      const c = { responsive: true, displaylogo: false, ...config };
      Plotly.newPlot(containerRef.current, spec.data, spec.layout, c);
    }).catch(console.error);
  }, [data, layout, config, chart]);

  return <div ref={containerRef} style={{ width: '100%', minHeight: '300px', ...style }} />;
};

export default PlotlyChart;