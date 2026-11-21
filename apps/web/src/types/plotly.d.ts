declare module "plotly.js-basic-dist-min" {
  export interface PlotlyTrace {
    type?: string;
    name?: string;
    x?: Array<string | number>;
    y?: Array<string | number>;
    text?: string[];
    hovertemplate?: string;
    orientation?: "h" | "v";
    error_y?: {
      type: string;
      array?: number[];
      arrayminus?: number[];
      symmetric?: boolean;
      visible: boolean;
      color?: string;
      thickness?: number;
      width?: number;
    };
    error_x?: {
      type: string;
      array?: number[];
      arrayminus?: number[];
      symmetric?: boolean;
      visible: boolean;
      color?: string;
    };
    marker?: {
      color?: string | string[];
      size?: number;
      line?: { color?: string; width?: number };
    };
    line?: {
      color?: string;
      width?: number;
      dash?: string;
    };
    mode?: string;
  }

  export interface PlotlyAxis {
    title?: string | { text: string; font?: { size?: number; color?: string } };
    rangemode?: string;
    range?: [number, number];
    gridcolor?: string;
    zerolinecolor?: string;
    tickangle?: number;
    tickfont?: { size?: number; color?: string };
    automargin?: boolean;
  }

  export interface PlotlyLayout {
    title?: string | { text: string; font?: { size?: number; color?: string } };
    barmode?: string;
    paper_bgcolor?: string;
    plot_bgcolor?: string;
    colorway?: string[];
    font?: { family?: string; size?: number; color?: string };
    legend?: {
      orientation?: "h" | "v";
      x?: number;
      y?: number;
      bgcolor?: string;
      font?: { size?: number; color?: string };
    };
    xaxis?: PlotlyAxis;
    yaxis?: PlotlyAxis;
    margin?: { l?: number; r?: number; t?: number; b?: number };
    height?: number;
    shapes?: Array<{
      type?: string;
      x0?: number | string;
      x1?: number | string;
      y0?: number | string;
      y1?: number | string;
      xref?: string;
      yref?: string;
      line?: { color?: string; width?: number; dash?: string };
    }>;
    annotations?: Array<{
      text: string;
      xref?: string;
      yref?: string;
      x?: number | string;
      y?: number | string;
      showarrow?: boolean;
      font?: { size?: number; color?: string };
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
