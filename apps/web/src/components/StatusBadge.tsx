import React from "react";

export type BadgeTone = "ruo" | "synth" | "ok" | "warn" | "neutral";

interface StatusBadgeProps {
  label: string;
  tone?: BadgeTone;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ label, tone = "neutral" }) => {
  return <span className={`badge badge-${tone}`}>{label}</span>;
};
