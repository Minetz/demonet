import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

/** Derive the primary hue from a hash (same algorithm as Fingerprint.jsx). */
function hashHue(hash) {
  if (!hash || hash.length < 2) return 240;
  return (parseInt(hash.slice(0, 2), 16) / 255) * 360;
}

export default function Constellation({ points, highlightHash }) {
  const svgRef = useRef();
  const tooltipRef = useRef();

  useEffect(() => {
    if (!points || points.length === 0) return;

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth || 600;
    const height = 400;

    svg.attr('viewBox', `0 0 ${width} ${height}`);
    svg.selectAll('*').remove();

    // Scale points to fit — guard against degenerate extents (all same value)
    const xExtent = d3.extent(points, (d) => d.x);
    const yExtent = d3.extent(points, (d) => d.y);
    if (xExtent[0] === xExtent[1]) { xExtent[0] -= 1; xExtent[1] += 1; }
    if (yExtent[0] === yExtent[1]) { yExtent[0] -= 1; yExtent[1] += 1; }
    const xScale = d3.scaleLinear().domain(xExtent).range([60, width - 60]);
    const yScale = d3.scaleLinear().domain(yExtent).range([60, height - 60]);

    // Draw connections between nearby points
    const threshold = Math.max(width, height) * 0.15;
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const x1 = xScale(points[i].x);
        const y1 = yScale(points[i].y);
        const x2 = xScale(points[j].x);
        const y2 = yScale(points[j].y);
        const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        if (dist < threshold) {
          svg
            .append('line')
            .attr('x1', x1)
            .attr('y1', y1)
            .attr('x2', x2)
            .attr('y2', y2)
            .attr('stroke', 'rgba(99, 102, 241, 0.1)')
            .attr('stroke-width', 1);
        }
      }
    }

    // Tooltip — use a stable ref, not body-append, to avoid leaks
    const tooltip = d3.select(tooltipRef.current);

    // Draw points with hash-derived colors (matches Fingerprint hue)
    svg
      .selectAll('circle')
      .data(points)
      .enter()
      .append('circle')
      .attr('cx', (d) => xScale(d.x))
      .attr('cy', (d) => yScale(d.y))
      .attr('r', (d) => (d.hash === highlightHash ? 8 : 4.5))
      .attr('fill', (d) => {
        const hue = hashHue(d.hash);
        return d.hash === highlightHash
          ? `hsl(${hue}, 80%, 65%)`
          : `hsla(${hue}, 70%, 60%, 0.6)`;
      })
      .attr('stroke', (d) => {
        if (d.hash !== highlightHash) return 'none';
        const hue = hashHue(d.hash);
        return `hsl(${hue}, 70%, 75%)`;
      })
      .attr('stroke-width', 2)
      .style('filter', (d) => {
        if (d.hash !== highlightHash) return 'none';
        const hue = hashHue(d.hash);
        return `drop-shadow(0 0 8px hsla(${hue}, 80%, 60%, 0.6))`;
      })
      .style('cursor', 'pointer')
      .on('mouseover', (event, d) => {
        tooltip
          .style('opacity', '1')
          .html(
            `<strong>#${d.hash}</strong>${d.region ? ` &middot; ${d.region}` : ''}<br/>${d.text_preview}`
          );
      })
      .on('mousemove', (event) => {
        const rect = svgRef.current.getBoundingClientRect();
        tooltip
          .style('left', event.clientX - rect.left + 12 + 'px')
          .style('top', event.clientY - rect.top - 28 + 'px');
      })
      .on('mouseout', () => {
        tooltip.style('opacity', '0');
      });
  }, [points, highlightHash]);

  if (!points || points.length === 0) {
    return (
      <div className="w-full max-w-2xl mx-auto mt-8 p-8 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] text-center">
        <p className="text-[var(--color-text-dim)]">
          Be the first to share your take. The constellation grows with every voice.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto mt-8">
      <h3 className="text-sm font-semibold text-[var(--color-text-dim)] mb-2">
        Opinion constellation ({points.length} voices)
      </h3>
      <div className="rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] overflow-hidden relative">
        <svg ref={svgRef} className="w-full" style={{ height: 400 }} />
        {/* Tooltip rendered inside the container — no body leak */}
        <div
          ref={tooltipRef}
          style={{
            position: 'absolute',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '12px',
            color: 'var(--color-text)',
            pointerEvents: 'none',
            opacity: 0,
            maxWidth: '250px',
            zIndex: 10,
            transition: 'opacity 0.1s',
          }}
        />
      </div>
    </div>
  );
}
