"""Server-rendered share page for opinion cards with Open Graph metadata."""

import math
from html import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.opinions import get_opinion_by_hash

share_router = APIRouter()


def _generate_fingerprint_svg(hash_str: str, size: int = 160) -> str:
    """Generate the same fingerprint SVG as the frontend Fingerprint.jsx component."""
    if not hash_str or len(hash_str) < 16:
        return ""

    b = []
    for i in range(0, 16, 2):
        b.append(int(hash_str[i : i + 2], 16))

    cx = size / 2
    cy = size / 2
    outer_r = size * 0.42

    hue1 = (b[0] / 255) * 360
    hue2 = (hue1 + 90 + (b[1] / 255) * 180) % 360
    segments = 3 + (b[2] % 6)
    inner_ratio = 0.25 + (b[3] / 255) * 0.2
    mid_ratio = 0.55 + (b[4] / 255) * 0.15
    base_angle = (b[5] / 255) * math.pi * 2
    dot_scale = 0.6 + (b[6] / 255) * 0.8
    connect_bits = b[7]

    inner_r = outer_r * inner_ratio
    mid_r = outer_r * mid_ratio
    step = (math.pi * 2) / segments

    def ring(radius, offset=0):
        return [
            (cx + math.cos(i * step + base_angle + offset) * radius,
             cy + math.sin(i * step + base_angle + offset) * radius)
            for i in range(segments)
        ]

    outer = ring(outer_r)
    mid = ring(mid_r, step / 2)
    inner = ring(inner_r)

    primary = f"hsl({hue1:.0f}, 70%, 65%)"
    primary_dim = f"hsla({hue1:.0f}, 70%, 65%, 0.4)"
    secondary = f"hsl({hue2:.0f}, 60%, 55%)"
    secondary_dim = f"hsla({hue2:.0f}, 60%, 55%, 0.35)"
    glow = f"hsla({hue1:.0f}, 80%, 60%, 0.2)"
    glow_id = hash_str[:8]

    lines = []

    # Outer polygon
    for i in range(segments):
        j = (i + 1) % segments
        lines.append(
            f'<line x1="{outer[i][0]:.1f}" y1="{outer[i][1]:.1f}" '
            f'x2="{outer[j][0]:.1f}" y2="{outer[j][1]:.1f}" '
            f'stroke="{primary}" stroke-width="0.8" opacity="0.35"/>'
        )

    # Mid polygon
    for i in range(segments):
        j = (i + 1) % segments
        lines.append(
            f'<line x1="{mid[i][0]:.1f}" y1="{mid[i][1]:.1f}" '
            f'x2="{mid[j][0]:.1f}" y2="{mid[j][1]:.1f}" '
            f'stroke="{secondary}" stroke-width="0.6" opacity="0.3"/>'
        )

    # Inner polygon
    for i in range(segments):
        j = (i + 1) % segments
        lines.append(
            f'<line x1="{inner[i][0]:.1f}" y1="{inner[i][1]:.1f}" '
            f'x2="{inner[j][0]:.1f}" y2="{inner[j][1]:.1f}" '
            f'stroke="{primary}" stroke-width="0.5" opacity="0.25"/>'
        )

    # Spokes: outer-mid, mid-inner
    for i in range(segments):
        lines.append(
            f'<line x1="{outer[i][0]:.1f}" y1="{outer[i][1]:.1f}" '
            f'x2="{mid[i][0]:.1f}" y2="{mid[i][1]:.1f}" '
            f'stroke="{primary_dim}" stroke-width="0.6"/>'
        )
        lines.append(
            f'<line x1="{mid[i][0]:.1f}" y1="{mid[i][1]:.1f}" '
            f'x2="{inner[i][0]:.1f}" y2="{inner[i][1]:.1f}" '
            f'stroke="{secondary_dim}" stroke-width="0.5"/>'
        )

    # Cross-connections
    for i in range(segments):
        if connect_bits & (1 << (i % 8)):
            j = (i + 1) % segments
            lines.append(
                f'<line x1="{outer[i][0]:.1f}" y1="{outer[i][1]:.1f}" '
                f'x2="{mid[j][0]:.1f}" y2="{mid[j][1]:.1f}" '
                f'stroke="{primary_dim}" stroke-width="0.4"/>'
            )
        if connect_bits & (1 << ((i + 4) % 8)):
            lines.append(
                f'<line x1="{inner[i][0]:.1f}" y1="{inner[i][1]:.1f}" '
                f'x2="{cx:.1f}" y2="{cy:.1f}" '
                f'stroke="{secondary_dim}" stroke-width="0.4"/>'
            )

    # Dots
    outer_dot_r = 2.5 * dot_scale
    mid_dot_r = 2.0 * dot_scale
    inner_dot_r = 1.5 * dot_scale

    dots = []
    for p in outer:
        dots.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{outer_dot_r:.1f}" fill="{primary}"/>')
    for p in mid:
        dots.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{mid_dot_r:.1f}" fill="{secondary}"/>')
    for p in inner:
        dots.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{inner_dot_r:.1f}" fill="{primary}" opacity="0.8"/>')

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><radialGradient id="g-{glow_id}">'
        f'<stop offset="0%" stop-color="{glow}"/>'
        f'<stop offset="70%" stop-color="transparent"/>'
        f'</radialGradient></defs>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{outer_r * 1.2:.1f}" fill="url(#g-{glow_id})"/>'
        + "".join(lines)
        + "".join(dots)
        + f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" fill="white" opacity="0.85"/>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="none" stroke="{primary}" stroke-width="0.6" opacity="0.3"/>'
        f"</svg>"
    )


@share_router.get("/s/{opinion_hash}", response_class=HTMLResponse)
async def share_page(opinion_hash: str, request: Request, db: AsyncSession = Depends(get_db)):
    opinion = await get_opinion_by_hash(db, opinion_hash)

    if not opinion:
        return HTMLResponse(
            content="<html><body><h1>Opinion not found</h1></body></html>",
            status_code=404,
        )

    text = escape(opinion.anonymized_text)
    fingerprint = _generate_fingerprint_svg(opinion.hash)
    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/s/{opinion.hash}"

    og_title = f"Opinion #{opinion.hash} — The World's Take"
    og_description = text[:200] + ("..." if len(text) > 200 else "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{escape(og_title)}</title>
<meta property="og:type" content="article"/>
<meta property="og:title" content="{escape(og_title)}"/>
<meta property="og:description" content="{escape(og_description)}"/>
<meta property="og:url" content="{escape(share_url)}"/>
<meta property="og:site_name" content="The World's Take"/>
<meta name="twitter:card" content="summary"/>
<meta name="twitter:title" content="{escape(og_title)}"/>
<meta name="twitter:description" content="{escape(og_description)}"/>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0f;color:#e4e4ef;font-family:'Inter',system-ui,sans-serif;
  min-height:100vh;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:24px}}
.card{{background:#12121a;border:1px solid #1e1e2e;border-radius:20px;
  padding:32px;max-width:480px;width:100%}}
.header{{display:flex;align-items:center;gap:20px;margin-bottom:20px}}
.sig{{flex:1;min-width:0}}
.label{{font-size:11px;text-transform:uppercase;letter-spacing:0.2em;color:#8888a0}}
.hash{{font-family:monospace;font-size:18px;color:#6366f1;margin-top:4px}}
.text{{font-size:15px;line-height:1.6;color:#c4c4d4;margin-bottom:16px}}
.region{{font-size:13px;color:#8888a0}}
.lang{{display:inline-block;padding:2px 8px;border-radius:6px;
  background:#1e1e2e;color:#8888a0;font-size:12px;margin-top:8px}}
.cta{{text-align:center;margin-top:24px}}
.cta a{{color:#6366f1;text-decoration:none;font-size:14px}}
.cta a:hover{{text-decoration:underline}}
.brand{{font-size:11px;text-transform:uppercase;letter-spacing:0.3em;
  color:#8888a0;margin-bottom:16px;text-align:center}}
.footer{{text-align:center;margin-top:24px;font-size:12px;color:#666}}
</style>
</head>
<body>
<p class="brand">The World's Take</p>
<div class="card">
  <div class="header">
    {fingerprint}
    <div class="sig">
      <p class="label">Opinion signature</p>
      <p class="hash">#{escape(opinion.hash)}</p>
    </div>
  </div>
  <p class="text">&ldquo;{text}&rdquo;</p>
  {f'<p class="region">from {escape(opinion.region)}</p>' if opinion.region else ''}
  {f'<span class="lang">translated from {escape(opinion.language)}</span>' if opinion.language and opinion.language != 'en' else ''}
</div>
<div class="cta">
  <a href="/">Share your own take &rarr;</a>
</div>
<p class="footer">Open source. Open protocol. Your identity is never stored.</p>
</body>
</html>"""

    return HTMLResponse(content=html)
