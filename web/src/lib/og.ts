/**
 * Generative OpenGraph cards.
 *
 * `renderOgCard` returns a 1200×630 SVG ready for use as the
 * `og:image` for a per-record page. The design is editorial and
 * monochrome — no chart rendering yet — but it's *specific* (titles,
 * subtitles, kickers, footers all derived from the page record), which
 * is the primary value over the project's single static `/og.svg`.
 *
 * Optional `points` overlay: if a small 2D point cloud is passed, the
 * card renders a sparkline-style preview in the footer. This is enough
 * to make link previews of finding pages feel distinct.
 */

export interface OgCardOptions {
  /** Eyebrow above the title, e.g. "Finding · psychometric". */
  kicker?: string;
  /** Main heading, ≤ ~80 chars renders well. */
  title: string;
  /** Secondary line under the title — paper citation, slice metadata. */
  subtitle?: string;
  /** Footer line — id, year, n trials. */
  footer?: string;
  /** Optional small line chart drawn in the bottom-right. */
  points?: Array<{ x: number; y: number }>;
  /** Domain of the sparkline y axis. Defaults to data range. */
  yDomain?: [number, number];
  /** Accent colour as a hex; defaults to the atlas accent. */
  accent?: string;
}

const WIDTH = 1200;
const HEIGHT = 630;

// Token-aligned palette. These mirror the atlas design tokens; OG
// images live outside the page DOM so we can't read CSS variables here.
const PALETTE = {
  bg: "#f8fafc", // surface
  bgRaised: "#ffffff", // surface-raised
  fg: "#0f172a", // fg
  fgSecondary: "#334155", // fg-secondary
  fgMuted: "#64748b", // fg-muted
  rule: "#e2e8f0",
  accent: "#2b5ea0",
  accentSoft: "#e8eef7",
};

function escape(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wrapText(input: string, maxChars: number, maxLines: number): string[] {
  const words = input.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const next = current.length === 0 ? word : `${current} ${word}`;
    if (next.length <= maxChars) {
      current = next;
    } else {
      if (current.length > 0) lines.push(current);
      current = word;
      if (lines.length >= maxLines - 1) {
        // Truncate the last line to fit; ellipsise.
        const remainingWords = words.slice(words.indexOf(word));
        const tail = remainingWords.join(" ");
        lines.push(
          tail.length > maxChars ? `${tail.slice(0, maxChars - 1)}…` : tail,
        );
        return lines;
      }
    }
  }
  if (current.length > 0) lines.push(current);
  return lines;
}

function renderSparkline(
  points: Array<{ x: number; y: number }>,
  yDomain: [number, number] | undefined,
  accent: string,
): string {
  if (points.length < 2) return "";
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const [yMin, yMax] = yDomain ?? [Math.min(...ys), Math.max(...ys)];
  if (xMax === xMin || yMax === yMin) return "";

  // Sparkline frame inside the card footer, right-aligned.
  const x0 = WIDTH - 360;
  const y0 = HEIGHT - 200;
  const w = 280;
  const h = 130;

  function px(x: number): number {
    return x0 + ((x - xMin) / (xMax - xMin)) * w;
  }
  function py(y: number): number {
    return y0 + h - ((y - yMin) / (yMax - yMin)) * h;
  }

  const sorted = [...points].sort((a, b) => a.x - b.x);
  const path = sorted
    .map((p, i) => `${i === 0 ? "M" : "L"} ${px(p.x).toFixed(1)} ${py(p.y).toFixed(1)}`)
    .join(" ");

  const dots = sorted
    .map(
      (p) =>
        `<circle cx="${px(p.x).toFixed(1)}" cy="${py(p.y).toFixed(1)}" r="3.5" fill="${accent}" />`,
    )
    .join("");

  // Horizontal midline reference (psychometric chance, for example) — a
  // quiet visual anchor; only shown when the y domain straddles 0.5.
  const showMid = yMin <= 0.5 && yMax >= 0.5;
  const mid = showMid
    ? `<line x1="${x0}" y1="${py(0.5).toFixed(1)}" x2="${x0 + w}" y2="${py(0.5).toFixed(1)}" stroke="${PALETTE.rule}" stroke-width="1" stroke-dasharray="4 4" />`
    : "";

  return `
    <g>
      <rect x="${x0 - 18}" y="${y0 - 18}" width="${w + 36}" height="${h + 36}" rx="12" fill="${PALETTE.bgRaised}" stroke="${PALETTE.rule}" />
      ${mid}
      <path d="${path}" fill="none" stroke="${accent}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
      ${dots}
    </g>
  `;
}

export function renderOgCard(options: OgCardOptions): string {
  const accent = options.accent ?? PALETTE.accent;
  const titleLines = wrapText(options.title, 38, 3);
  const subtitleLines = options.subtitle
    ? wrapText(options.subtitle, 56, 2)
    : [];

  // Title block coordinates.
  const titleX = 80;
  let cursorY = 200;
  const titleLineHeight = 84;
  const titleTspans = titleLines
    .map((line, i) => {
      const y = cursorY + i * titleLineHeight;
      return `<tspan x="${titleX}" y="${y}">${escape(line)}</tspan>`;
    })
    .join("");
  cursorY = cursorY + titleLines.length * titleLineHeight;

  const subtitleTspans = subtitleLines
    .map((line, i) => {
      const y = cursorY + 24 + i * 40;
      return `<tspan x="${titleX}" y="${y}">${escape(line)}</tspan>`;
    })
    .join("");

  const sparkline = options.points
    ? renderSparkline(options.points, options.yDomain, accent)
    : "";

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img" aria-label="${escape(options.title)}">
  <rect width="${WIDTH}" height="${HEIGHT}" fill="${PALETTE.bg}" />
  <rect x="0" y="0" width="8" height="${HEIGHT}" fill="${accent}" />
  <g font-family="-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif">
    <text x="${titleX}" y="100" font-size="28" font-weight="600" fill="${accent}" letter-spacing="2">behavtaskatlas</text>
    ${
      options.kicker
        ? `<text x="${titleX}" y="148" font-size="22" font-weight="500" fill="${PALETTE.fgMuted}" letter-spacing="1.5">${escape(options.kicker.toUpperCase())}</text>`
        : ""
    }
    <text font-size="64" font-weight="600" fill="${PALETTE.fg}" font-family="'Iowan Old Style', 'Charter', 'Source Serif Pro', Georgia, serif">${titleTspans}</text>
    ${
      subtitleLines.length > 0
        ? `<text font-size="30" fill="${PALETTE.fgSecondary}">${subtitleTspans}</text>`
        : ""
    }
    ${
      options.footer
        ? `<text x="${titleX}" y="${HEIGHT - 60}" font-size="22" fill="${PALETTE.fgMuted}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">${escape(options.footer)}</text>`
        : ""
    }
  </g>
  ${sparkline}
</svg>`;
}
