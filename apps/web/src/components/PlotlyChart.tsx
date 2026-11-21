import React, { useEffect, useMemo, useRef } from "react";
import type { PlotlyLayout, PlotlyTrace } from "plotly.js-basic-dist-min";

interface PlotlyChartProps {
  traces: PlotlyTrace[];
  layout: PlotlyLayout;
  ariaLabel: string;
  theme?: "dark" | "light";
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  traces,
  layout,
  ariaLabel,
  theme = "dark",
}) => {
  const hostRef = useRef<HTMLDivElement | null>(null);

  const themedLayout = useMemo<PlotlyLayout>(() => {
    const isDark = theme === "dark";
    const textColor = isDark ? "#cbd5e1" : "#1e293b";
    const gridColor = isDark ? "rgba(148, 163, 184, 0.16)" : "rgba(15, 23, 42, 0.1)";
    const zeroColor = isDark ? "rgba(148, 163, 184, 0.34)" : "rgba(15, 23, 42, 0.25)";
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: isDark ? "rgba(8, 13, 22, 0.55)" : "rgba(248, 250, 253, 0.7)",
      colorway: isDark
        ? ["#38bdf8", "#f59e0b", "#10b981", "#a78bfa", "#fb7185", "#2dd4bf"]
        : ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"],
      font: {
        family: "Inter, system-ui, sans-serif",
        size: 12,
        color: textColor,
        ...layout.font,
      },
      legend: {
        orientation: "h",
        x: 0,
        y: 1.13,
        bgcolor: "rgba(0,0,0,0)",
        ...layout.legend,
      },
      ...layout,
      xaxis: {
        gridcolor: gridColor,
        zerolinecolor: zeroColor,
        automargin: true,
        ...layout.xaxis,
      },
      yaxis: {
        gridcolor: gridColor,
        zerolinecolor: zeroColor,
        automargin: true,
        ...layout.yaxis,
      },
    };
  }, [layout, theme]);

  useEffect(() => {
    let active = true;
    const el = hostRef.current;
    if (!el || typeof navigator === "undefined" || navigator.userAgent.includes("jsdom")) {
      return;
    }
    import("plotly.js-basic-dist-min")
      .then((mod) => {
        if (!active || !el) {
          return;
        }
        return mod.default.react(el, traces, themedLayout, {
          responsive: true,
          displayModeBar: false,
        });
      })
      .catch(() => undefined);

    return () => {
      active = false;
      import("plotly.js-basic-dist-min")
        .then((mod) => {
          if (el) {
            mod.default.purge(el);
          }
        })
        .catch(() => undefined);
    };
  }, [traces, themedLayout]);

  return <div ref={hostRef} role="img" aria-label={ariaLabel} />;
};
