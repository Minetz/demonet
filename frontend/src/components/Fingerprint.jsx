/**
 * Generative visual fingerprint — a unique geometric pattern derived
 * deterministically from an opinion hash. Each hash produces a distinct
 * crystalline/constellation shape that serves as the opinion's visual identity.
 */
export default function Fingerprint({ hash, size = 120, className = '' }) {
  if (!hash || hash.length < 16) return null;

  // Parse 16 hex chars into 8 byte values [0–255]
  const b = [];
  for (let i = 0; i < 16; i += 2) {
    b.push(parseInt(hash.slice(i, i + 2), 16));
  }

  const cx = size / 2;
  const cy = size / 2;
  const outerR = size * 0.42;

  // --- Derive visual parameters from hash bytes ---
  const hue1 = (b[0] / 255) * 360;
  const hue2 = (hue1 + 90 + (b[1] / 255) * 180) % 360;
  const segments = 3 + (b[2] % 6); // 3–8 fold symmetry
  const innerRatio = 0.25 + (b[3] / 255) * 0.2; // 0.25–0.45
  const midRatio = 0.55 + (b[4] / 255) * 0.15; // 0.55–0.70
  const baseAngle = (b[5] / 255) * Math.PI * 2;
  const dotScale = 0.6 + (b[6] / 255) * 0.8; // 0.6–1.4
  const connectBits = b[7]; // 8 bits controlling connection patterns

  const innerR = outerR * innerRatio;
  const midR = outerR * midRatio;

  const primary = `hsl(${hue1}, 70%, 65%)`;
  const primaryDim = `hsla(${hue1}, 70%, 65%, 0.4)`;
  const secondary = `hsl(${hue2}, 60%, 55%)`;
  const secondaryDim = `hsla(${hue2}, 60%, 55%, 0.35)`;
  const glow = `hsla(${hue1}, 80%, 60%, 0.2)`;

  // --- Generate ring points ---
  const step = (Math.PI * 2) / segments;

  const ring = (radius, offset = 0) =>
    Array.from({ length: segments }, (_, i) => {
      const a = i * step + baseAngle + offset;
      return { x: cx + Math.cos(a) * radius, y: cy + Math.sin(a) * radius };
    });

  const outer = ring(outerR);
  const mid = ring(midR, step / 2); // offset by half-step
  const inner = ring(innerR);

  // --- Build SVG elements ---
  const lines = [];
  const id = hash.slice(0, 8);

  // Outer polygon
  for (let i = 0; i < segments; i++) {
    const j = (i + 1) % segments;
    lines.push(
      <line key={`o${i}`} x1={outer[i].x} y1={outer[i].y}
        x2={outer[j].x} y2={outer[j].y}
        stroke={primary} strokeWidth={0.8} opacity={0.35} />
    );
  }

  // Mid polygon
  for (let i = 0; i < segments; i++) {
    const j = (i + 1) % segments;
    lines.push(
      <line key={`m${i}`} x1={mid[i].x} y1={mid[i].y}
        x2={mid[j].x} y2={mid[j].y}
        stroke={secondary} strokeWidth={0.6} opacity={0.3} />
    );
  }

  // Inner polygon
  for (let i = 0; i < segments; i++) {
    const j = (i + 1) % segments;
    lines.push(
      <line key={`i${i}`} x1={inner[i].x} y1={inner[i].y}
        x2={inner[j].x} y2={inner[j].y}
        stroke={primary} strokeWidth={0.5} opacity={0.25} />
    );
  }

  // Spokes: outer ↔ mid (always)
  for (let i = 0; i < segments; i++) {
    lines.push(
      <line key={`om${i}`} x1={outer[i].x} y1={outer[i].y}
        x2={mid[i].x} y2={mid[i].y}
        stroke={primaryDim} strokeWidth={0.6} />
    );
  }

  // Spokes: mid ↔ inner (always)
  for (let i = 0; i < segments; i++) {
    lines.push(
      <line key={`mi${i}`} x1={mid[i].x} y1={mid[i].y}
        x2={inner[i].x} y2={inner[i].y}
        stroke={secondaryDim} strokeWidth={0.5} />
    );
  }

  // Cross-connections driven by connectBits
  for (let i = 0; i < segments; i++) {
    // Outer to next mid (star pattern)
    if (connectBits & (1 << (i % 8))) {
      const j = (i + 1) % segments;
      lines.push(
        <line key={`x${i}`} x1={outer[i].x} y1={outer[i].y}
          x2={mid[j].x} y2={mid[j].y}
          stroke={primaryDim} strokeWidth={0.4} />
      );
    }
    // Inner to center
    if (connectBits & (1 << ((i + 4) % 8))) {
      lines.push(
        <line key={`ic${i}`} x1={inner[i].x} y1={inner[i].y}
          x2={cx} y2={cy}
          stroke={secondaryDim} strokeWidth={0.4} />
      );
    }
  }

  // Dots
  const outerDotR = 2.5 * dotScale;
  const midDotR = 2 * dotScale;
  const innerDotR = 1.5 * dotScale;

  const dots = [
    ...outer.map((p, i) => (
      <circle key={`od${i}`} cx={p.x} cy={p.y} r={outerDotR}
        fill={primary} />
    )),
    ...mid.map((p, i) => (
      <circle key={`md${i}`} cx={p.x} cy={p.y} r={midDotR}
        fill={secondary} />
    )),
    ...inner.map((p, i) => (
      <circle key={`id${i}`} cx={p.x} cy={p.y} r={innerDotR}
        fill={primary} opacity={0.8} />
    )),
  ];

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      role="img"
      aria-label={`Opinion fingerprint #${hash}`}
    >
      <defs>
        <radialGradient id={`glow-${id}`}>
          <stop offset="0%" stopColor={glow} />
          <stop offset="70%" stopColor="transparent" />
        </radialGradient>
      </defs>

      {/* Ambient glow */}
      <circle cx={cx} cy={cy} r={outerR * 1.2} fill={`url(#glow-${id})`} />

      {/* Structure */}
      {lines}

      {/* Nodes */}
      {dots}

      {/* Center */}
      <circle cx={cx} cy={cy} r={2.5} fill="white" opacity={0.85} />
      <circle cx={cx} cy={cy} r={5} fill="none"
        stroke={primary} strokeWidth={0.6} opacity={0.3} />
    </svg>
  );
}
