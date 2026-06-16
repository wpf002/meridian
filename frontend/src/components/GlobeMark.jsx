// Globe with meridian lines — the Meridian logo mark.
export default function GlobeMark({ size = 38, spin = true }) {
  return (
    <span
      className="relative inline-flex items-center justify-center rounded-full"
      style={{ width: size, height: size }}
    >
      {/* soft halo so it reads as a brand mark */}
      <span
        className="absolute inset-0 rounded-full"
        style={{ boxShadow: '0 0 18px -2px rgba(38,227,160,0.35), inset 0 0 10px -4px rgba(57,182,246,0.4)' }}
      />
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        style={spin ? { animation: 'spin-slow 40s linear infinite' } : undefined}
      >
        <defs>
          <linearGradient id="mg" x1="6" y1="6" x2="58" y2="58" gradientUnits="userSpaceOnUse">
            <stop stopColor="#26e3a0" />
            <stop offset="1" stopColor="#39b6f6" />
          </linearGradient>
          <radialGradient id="sphere" cx="38%" cy="34%" r="72%">
            <stop offset="0%" stopColor="rgba(57,182,246,0.18)" />
            <stop offset="60%" stopColor="rgba(38,227,160,0.06)" />
            <stop offset="100%" stopColor="rgba(4,7,11,0)" />
          </radialGradient>
        </defs>

        {/* sphere body */}
        <circle cx="32" cy="32" r="26" fill="url(#sphere)" />
        <circle cx="32" cy="32" r="26" stroke="url(#mg)" strokeWidth="1.8" />

        {/* latitude lines */}
        <line x1="6" y1="32" x2="58" y2="32" stroke="#39b6f6" strokeWidth="1.1" opacity="0.55" />
        <ellipse cx="32" cy="20" rx="24" ry="6.5" stroke="#39b6f6" strokeWidth="0.9" opacity="0.32" />
        <ellipse cx="32" cy="44" rx="24" ry="6.5" stroke="#39b6f6" strokeWidth="0.9" opacity="0.32" />

        {/* meridian (longitude) lines */}
        <ellipse cx="32" cy="32" rx="10" ry="26" stroke="#26e3a0" strokeWidth="1.1" opacity="0.7" />
        <ellipse cx="32" cy="32" rx="20" ry="26" stroke="#26e3a0" strokeWidth="0.9" opacity="0.42" />
        {/* prime meridian — the bright reference line */}
        <line x1="32" y1="6" x2="32" y2="58" stroke="#26e3a0" strokeWidth="1.6" opacity="0.95" />
      </svg>
    </span>
  )
}
