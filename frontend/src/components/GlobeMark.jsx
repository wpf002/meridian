// Globe with meridian lines — the Meridian brand mark.
export default function GlobeMark({ size = 30, spin = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      style={spin ? { animation: 'spin-slow 36s linear infinite' } : undefined}
    >
      <defs>
        <linearGradient id="mg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
          <stop stopColor="#26e3a0" />
          <stop offset="1" stopColor="#39b6f6" />
        </linearGradient>
      </defs>
      <circle cx="32" cy="32" r="27" stroke="url(#mg)" strokeWidth="1.5" opacity="0.9" />
      {/* latitude lines */}
      <ellipse cx="32" cy="32" rx="27" ry="9" stroke="#39b6f6" strokeWidth="1" opacity="0.45" />
      <ellipse cx="32" cy="20" rx="22" ry="5.5" stroke="#39b6f6" strokeWidth="0.8" opacity="0.3" />
      <ellipse cx="32" cy="44" rx="22" ry="5.5" stroke="#39b6f6" strokeWidth="0.8" opacity="0.3" />
      {/* meridian (longitude) lines */}
      <ellipse cx="32" cy="32" rx="9" ry="27" stroke="#26e3a0" strokeWidth="1.1" opacity="0.65" />
      <ellipse cx="32" cy="32" rx="20" ry="27" stroke="#26e3a0" strokeWidth="0.9" opacity="0.4" />
      <line x1="32" y1="5" x2="32" y2="59" stroke="#26e3a0" strokeWidth="1.3" opacity="0.85" />
    </svg>
  )
}
