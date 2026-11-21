import React from "react";

export type BadgeTone = "ruo" | "synth" | "ok" | "warn" | "info" | "neutral";

interface StatusBadgeProps {
  label: string;
  tone?: BadgeTone;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ label, tone = "neutral" }) => {
  return (
    <span className={`badge badge-${tone}`}>
      <span className="badge-dot" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
};
