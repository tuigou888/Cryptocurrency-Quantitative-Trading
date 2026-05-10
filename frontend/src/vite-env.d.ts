/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

declare module 'plotly.js' {
  export function newPlot(
    gd: HTMLElement,
    data: Array<Partial<Plotly.PlotData>>,
    layout?: Partial<Plotly.Layout>,
    config?: Partial<Plotly.Config>
  ): Promise<void>;
}

declare module 'react-plotly.js' {
  import React from 'react';
  interface PlotParams {
    data: Array<Partial<Plotly.PlotData>>;
    layout?: Partial<Plotly.Layout>;
    config?: Partial<Plotly.Config>;
    style?: React.CSSProperties;
  }
  const Plot: React.FC<PlotParams>;
  export default Plot;
}

declare module 'vue-plotly' {
  import { DefineComponent } from 'vue';
  const component: DefineComponent<{}, {}, any>;
  export default component;
}
