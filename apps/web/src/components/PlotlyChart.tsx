import React, { useEffect, useRef } from "react";
import type { PlotlyLayout, PlotlyTrace } from "plotly.js-basic-dist-min";

interface PlotlyChartProps {
  traces: PlotlyTrace[];
  layout: PlotlyLayout;
  ariaLabel: string;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({ traces, layout, ariaLabel }) => {
  const hostRef = useRef<HTMLDivElement | null>(null);

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
        return mod.default.react(el, traces, layout, {
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
  }, [traces, layout]);

  return <div ref={hostRef} role="img" aria-label={ariaLabel} />;
};
