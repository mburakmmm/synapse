declare module "plotly.js-basic-dist-min" {
  export interface PlotlyTrace {
    type?: string;
    name?: string;
    x?: Array<string | number>;
    y?: number[];
    error_y?: {
      type: string;
      array: number[];
      visible: boolean;
    };
    marker?: { color?: string | string[] };
    mode?: string;
  }

  export interface PlotlyLayout {
    title?: string | { text: string };
    barmode?: string;
    xaxis?: { title?: string | { text: string } };
    yaxis?: { title?: string | { text: string }; rangemode?: string; range?: [number, number] };
    margin?: { l?: number; r?: number; t?: number; b?: number };
    height?: number;
    annotations?: Array<{
      text: string;
      xref?: string;
      yref?: string;
      x?: number;
      y?: number;
      showarrow?: boolean;
      font?: { size?: number };
    }>;
  }

  export interface PlotlyStatic {
    react: (
      el: HTMLElement,
      data: PlotlyTrace[],
      layout?: PlotlyLayout,
      config?: { responsive?: boolean; displayModeBar?: boolean },
    ) => Promise<void>;
    purge: (el: HTMLElement) => void;
  }

  const Plotly: PlotlyStatic;
  export default Plotly;
}
