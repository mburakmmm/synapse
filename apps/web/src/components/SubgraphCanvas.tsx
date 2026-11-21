import React, { useMemo, useState } from "react";
import type { SubgraphResponse } from "../api";
import { useI18n } from "../i18n/LanguageContext";
import { StatusBadge } from "./StatusBadge";

const NT_COLORS: Record<string, string> = {
  ACH: "#38bdf8",
  GABA: "#f43f5e",
  GLUT: "#f59e0b",
  DA: "#a78bfa",
  SER: "#10b981",
  OCT: "#2dd4bf",
  UNKNOWN: "#94a3b8",
};

function ntColor(nt: string | null): string {
  const key = (nt ?? "UNKNOWN").toUpperCase();
  return NT_COLORS[key] ?? NT_COLORS.UNKNOWN;
}

interface SubgraphCanvasProps {
  subgraph: SubgraphResponse;
}

interface PositionedNode {
  source_neuron_id: string;
  neurotransmitter: string | null;
  is_seed: boolean;
  x: number;
  y: number;
}

export const SubgraphCanvas: React.FC<SubgraphCanvasProps> = ({ subgraph }) => {
  const { t } = useI18n();
  const [selectedId, setSelectedId] = useState<string | null>(
    subgraph.nodes[0]?.source_neuron_id ?? null,
  );
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const width = 640;
  const height = 340;
  const cx = width / 2;
  const cy = height / 2;

  const { positioned, nodeMap, visibleEdges } = useMemo(() => {
    const cappedNodes = [...subgraph.nodes].slice(0, 72);
    const seeds = cappedNodes
      .filter((n) => n.is_seed)
      .sort((a, b) => a.source_neuron_id.localeCompare(b.source_neuron_id));
    const others = cappedNodes
      .filter((n) => !n.is_seed)
      .sort((a, b) => a.source_neuron_id.localeCompare(b.source_neuron_id));

    const out: PositionedNode[] = [];
    seeds.forEach((n, idx) => {
      if (seeds.length === 1) {
        out.push({ ...n, x: cx, y: cy });
      } else {
        const angle = (2 * Math.PI * idx) / seeds.length - Math.PI / 2;
        out.push({
          ...n,
          x: cx + 44 * Math.cos(angle),
          y: cy + 44 * Math.sin(angle),
        });
      }
    });

    const ringSplit = others.length > 26 ? Math.ceil(others.length / 2) : others.length;
    const innerRing = others.slice(0, ringSplit);
    const outerRing = others.slice(ringSplit);

    innerRing.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / Math.max(innerRing.length, 1) - Math.PI / 2;
      out.push({
        ...n,
        x: cx + 115 * Math.cos(angle),
        y: cy + 102 * Math.sin(angle),
      });
    });

    outerRing.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / Math.max(outerRing.length, 1) - Math.PI / 3;
      out.push({
        ...n,
        x: cx + 235 * Math.cos(angle),
        y: cy + 142 * Math.sin(angle),
      });
    });

    const map = new Map<string, PositionedNode>();
    out.forEach((n) => map.set(n.source_neuron_id, n));

    const edges = subgraph.edges
      .filter((e) => map.has(e.pre_neuron_id) && map.has(e.post_neuron_id))
      .slice(0, 180);

    return { positioned: out, nodeMap: map, visibleEdges: edges };
  }, [subgraph, cx, cy]);

  const activeNode =
    (selectedId ? nodeMap.get(selectedId) : undefined) ?? positioned[0] ?? null;

  const activeEdges = useMemo(() => {
    if (!activeNode) return { incoming: [], outgoing: [] };
    return {
      incoming: subgraph.edges.filter((e) => e.post_neuron_id === activeNode.source_neuron_id),
      outgoing: subgraph.edges.filter((e) => e.pre_neuron_id === activeNode.source_neuron_id),
    };
  }, [activeNode, subgraph.edges]);

  const handleCopy = (id: string) => {
    void navigator.clipboard?.writeText(id);
    setCopiedId(id);
    window.setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="subgraph-stage">
      <div className="card-header" style={{ marginBottom: 8 }}>
        <strong>{t("subgraphCanvasTitle")}</strong>
        <div className="subgraph-legend">
          {Object.entries(NT_COLORS).map(([nt, color]) => (
            <span key={nt} className="legend-swatch">
              <span className="legend-dot" style={{ background: color }} />
              <span>{nt}</span>
            </span>
          ))}
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "auto", maxHeight: 340, display: "block" }}
        role="img"
        aria-label={t("subgraphCanvasTitle")}
      >
        <defs>
          <marker
            id="synapse-arrow"
            viewBox="0 0 10 10"
            refX="14"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="rgba(148, 163, 184, 0.72)" />
          </marker>
        </defs>

        {visibleEdges.map((edge, idx) => {
          const src = nodeMap.get(edge.pre_neuron_id);
          const dst = nodeMap.get(edge.post_neuron_id);
          if (!src || !dst) return null;
          const highlighted =
            activeNode &&
            (edge.pre_neuron_id === activeNode.source_neuron_id ||
              edge.post_neuron_id === activeNode.source_neuron_id);
          const strokeWidth = Math.min(4.2, 0.9 + Math.log1p(edge.synapse_count) * 0.75);
          return (
            <line
              key={`${edge.pre_neuron_id}-${edge.post_neuron_id}-${idx}`}
              x1={src.x}
              y1={src.y}
              x2={dst.x}
              y2={dst.y}
              stroke={highlighted ? "#38bdf8" : "rgba(148, 163, 184, 0.34)"}
              strokeWidth={highlighted ? strokeWidth + 0.8 : strokeWidth}
              markerEnd="url(#synapse-arrow)"
            />
          );
        })}

        {positioned.map((node) => {
          const isSelected = activeNode?.source_neuron_id === node.source_neuron_id;
          const fill = ntColor(node.neurotransmitter);
          return (
            <g
              key={node.source_neuron_id}
              style={{ cursor: "pointer" }}
              onClick={() => setSelectedId(node.source_neuron_id)}
            >
              {node.is_seed && (
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={12}
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="3 2"
                />
              )}
              <circle
                cx={node.x}
                cy={node.y}
                r={node.is_seed ? 8 : 6}
                fill={fill}
                stroke={isSelected ? "#ffffff" : "#0f172a"}
                strokeWidth={isSelected ? 2.4 : 1.2}
              />
              <title>{`${node.source_neuron_id} (${node.neurotransmitter ?? "UNKNOWN"})`}</title>
            </g>
          );
        })}
      </svg>

      {activeNode && (
        <div
          style={{
            marginTop: 8,
            padding: "9px 12px",
            borderRadius: 8,
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 8,
            fontSize: "0.78rem",
          }}
        >
          <div>
            <strong>{t("subgraphNodeInspector")}: </strong>
            <span className="mono">{activeNode.source_neuron_id}</span>{" "}
            <StatusBadge
              label={activeNode.neurotransmitter ?? t("unknown")}
              tone={activeNode.neurotransmitter === "GABA" ? "synth" : "info"}
            />{" "}
            {activeNode.is_seed && <StatusBadge label="SEED" tone="warn" />}
            <span style={{ marginLeft: 10, color: "var(--text-secondary)" }}>
              in: <strong>{activeEdges.incoming.length}</strong> · out:{" "}
              <strong>{activeEdges.outgoing.length}</strong>
            </span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleCopy(activeNode.source_neuron_id)}
          >
            {copiedId === activeNode.source_neuron_id ? t("copied") : t("copyId")}
          </button>
        </div>
      )}
    </div>
  );
};
