export function GradientOrb({ className = "" }: { className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 100 100"
      className={`size-20 ${className}`}
      style={{ filter: "blur(0.4px)" }}
    >
      <defs>
        <radialGradient id="orb-a" cx="30%" cy="28%" r="75%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="45%" stopColor="#8fb6ff" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#5b5bd6" stopOpacity="0.1" />
        </radialGradient>
        <radialGradient id="orb-b" cx="72%" cy="74%" r="70%">
          <stop offset="0%" stopColor="#c9a7ff" stopOpacity="0.9" />
          <stop offset="60%" stopColor="#8b5cf6" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
        </radialGradient>
        <filter id="orb-soft" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
      </defs>
      <g filter="url(#orb-soft)">
        <circle cx="50" cy="50" r="34" fill="url(#orb-a)" />
        <circle cx="50" cy="50" r="34" fill="url(#orb-b)" />
      </g>
      <circle cx="43" cy="41" r="9" fill="#ffffff" opacity="0.55" filter="url(#orb-soft)" />
    </svg>
  );
}
