import React from "react";

interface IconProps {
  size?: number;
}

export const SynapseLogoIcon: React.FC<IconProps> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <circle cx="5" cy="7" r="2.2" stroke="currentColor" strokeWidth="1.8" />
    <circle cx="5" cy="17" r="2.2" stroke="currentColor" strokeWidth="1.8" />
    <circle cx="12.5" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.8" />
    <circle cx="19.5" cy="6.5" r="2.1" stroke="currentColor" strokeWidth="1.8" />
    <circle cx="19.5" cy="17.5" r="2.1" stroke="currentColor" strokeWidth="1.8" />
    <path
      d="M7 8L10.3 10.6M7 16L10.3 13.4M14.7 10.6L17.6 8M14.7 13.4L17.6 16"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    />
  </svg>
);

export const OverviewIcon: React.FC<IconProps> = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <rect x="3" y="3" width="8" height="8" rx="1.8" stroke="currentColor" strokeWidth="1.8" />
    <rect x="13" y="3" width="8" height="5" rx="1.8" stroke="currentColor" strokeWidth="1.8" />
    <rect x="13" y="10" width="8" height="11" rx="1.8" stroke="currentColor" strokeWidth="1.8" />
    <rect x="3" y="13" width="8" height="8" rx="1.8" stroke="currentColor" strokeWidth="1.8" />
  </svg>
);

export const ModulesIcon: React.FC<IconProps> = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M3 12H7L10 4L14 20L17 12H21"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const DatasetsIcon: React.FC<IconProps> = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" strokeWidth="1.8" />
    <path
      d="M4 6V12C4 13.7 7.6 15 12 15C16.4 15 20 13.7 20 12V6"
      stroke="currentColor"
      strokeWidth="1.8"
    />
    <path
      d="M4 12V18C4 19.7 7.6 21 12 21C16.4 21 20 19.7 20 18V12"
      stroke="currentColor"
      strokeWidth="1.8"
    />
  </svg>
);

export const ModelsIcon: React.FC<IconProps> = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M9 3H15M10 3V9L5.4 17.5C4.7 18.8 5.6 20.5 7.2 20.5H16.8C18.4 20.5 19.3 18.8 18.6 17.5L14 9V3"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const JobsIcon: React.FC<IconProps> = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <rect x="4" y="4" width="16" height="16" rx="2.2" stroke="currentColor" strokeWidth="1.8" />
    <path
      d="M9 12L11.2 14.2L15.5 9.8"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const ResultsIcon: React.FC<IconProps> = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M4 20V10M10 20V4M16 20V13M22 20H2"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
  </svg>
);

export const SunIcon: React.FC<IconProps> = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <circle cx="12" cy="12" r="4.2" stroke="currentColor" strokeWidth="1.8" />
    <path
      d="M12 2V4.5M12 19.5V22M4.9 4.9L6.7 6.7M17.3 17.3L19.1 19.1M2 12H4.5M19.5 12H22M4.9 19.1L6.7 17.3M17.3 6.7L19.1 4.9"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
  </svg>
);

export const MoonIcon: React.FC<IconProps> = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5A8.5 8.5 0 1 0 20.5 14.2Z"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const RefreshIcon: React.FC<IconProps> = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M20 5V10H15M4 19V14H9M5.2 9A7.5 7.5 0 0 1 18.6 7.5L20 10M4 14L5.4 16.5A7.5 7.5 0 0 0 18.8 15"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const ShieldIcon: React.FC<IconProps> = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M12 3L4.5 6V11.8C4.5 16.5 7.7 20.5 12 21.8C16.3 20.5 19.5 16.5 19.5 11.8V6L12 3Z"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinejoin="round"
    />
  </svg>
);

export const WarningIcon: React.FC<IconProps> = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M12 3.5L2.8 19.5H21.2L12 3.5Z"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinejoin="round"
    />
    <path d="M12 9.5V14M12 16.8V17.2" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
  </svg>
);

export const CodeIcon: React.FC<IconProps> = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      d="M8.5 7.5L4 12L8.5 16.5M15.5 7.5L20 12L15.5 16.5M13.5 5.5L10.5 18.5"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);
