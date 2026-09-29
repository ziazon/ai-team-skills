#!/usr/bin/env bash
# lh-audit.sh — run Lighthouse headlessly against a URL and print a parsed summary.
#
# The Chrome DevTools "Lighthouse" panel is just a GUI over the Lighthouse engine,
# which also ships as a CLI. This runs that engine with a PINNED config so results
# are comparable across runs (extensions disabled — a dirty Chrome profile can tank
# performance by 40+ points and Lighthouse will warn about it, exactly as seen on a
# real staging screenshot).
#
# Usage:
#   lh-audit.sh <url> [desktop|mobile|both] [outdir]
#
# Examples:
#   lh-audit.sh http://127.0.0.1:8083/ both ./.lighthouse
#
# Requires: node, Google Chrome, and the `lighthouse` CLI on PATH (install it
# yourself, e.g. `npm install -g lighthouse`; this script never downloads it).
# Outputs timestamped JSON + HTML per form-factor into <outdir> and prints:
#   category scores (Perf/A11y/BP/SEO), the Core Web Vitals metrics, and the top
#   opportunities/diagnostics ranked by estimated savings.

set -euo pipefail

URL="${1:?usage: lh-audit.sh <url> [desktop|mobile|both] [outdir]}"
FORM="${2:-both}"
OUTDIR="${3:-./.lighthouse}"
STAMP="$(date +%Y%m%d-%H%M%S)"
SLUG="$(printf '%s' "$URL" | sed -E 's#https?://##; s#[^a-zA-Z0-9]+#-#g; s#-+$##')"

command -v lighthouse >/dev/null 2>&1 || {
  echo "lh-audit.sh: the lighthouse CLI is not on PATH; install it first (e.g. npm install -g lighthouse)" >&2
  exit 1
}

mkdir -p "$OUTDIR"

run_one() {
  local preset="$1"          # desktop | mobile
  local base="${OUTDIR}/${STAMP}_${SLUG}_${preset}"
  echo "▶ Lighthouse ${preset}: ${URL}"
  # --preset=desktop applies desktop viewport + no throttling; omitting it = the
  # default MOBILE profile (Moto-G-class CPU 4x throttle + slow-4G) — much harsher,
  # and the fair target for a mobile-first audit. Keep both to compare like-for-like.
  local flags=(--only-categories=performance,accessibility,best-practices,seo,agentic-browsing
               --output=json --output=html
               --output-path="${base}"
               --chrome-flags="--headless=new --no-extensions --no-sandbox"
               --quiet)
  [ "$preset" = "desktop" ] && flags+=(--preset=desktop)
  lighthouse "$URL" "${flags[@]}" >/dev/null

  # Lighthouse writes <base>.report.json / <base>.report.html
  node - "$base" "$preset" <<'NODE'
const fs = require('fs');
const [base, preset] = process.argv.slice(2);
const r = JSON.parse(fs.readFileSync(base + '.report.json', 'utf8'));
const pct = c => r.categories[c] ? Math.round(r.categories[c].score * 100) : 'n/a';
const line = (l, v) => console.log('  ' + l.padEnd(16) + v);
console.log(`\n═══ ${preset.toUpperCase()} — ${r.finalDisplayedUrl || r.finalUrl} ═══`);
line('Performance', pct('performance'));
line('Accessibility', pct('accessibility'));
line('Best Practices', pct('best-practices'));
line('SEO', pct('seo'));
line('Agentic Brows.', pct('agentic-browsing'));
const m = id => (r.audits[id] && r.audits[id].displayValue) || '—';
console.log('  Core Web Vitals / metrics:');
line('  LCP', m('largest-contentful-paint'));
line('  TBT', m('total-blocking-time'));
line('  CLS', m('cumulative-layout-shift'));
line('  FCP', m('first-contentful-paint'));
line('  Speed Index', m('speed-index'));
line('  TTI', m('interactive'));
if ((r.runWarnings || []).length) {
  console.log('  ⚠ warnings:');
  r.runWarnings.forEach(w => console.log('    - ' + w));
}
// Top opportunities + diagnostics, ranked by estimated ms/byte savings.
const items = Object.values(r.audits)
  .filter(a => a.details && (a.details.type === 'opportunity' || a.numericValue) &&
               a.score !== null && a.score < 0.9 &&
               a.scoreDisplayMode !== 'informative' && a.scoreDisplayMode !== 'notApplicable')
  .map(a => ({
    title: a.title,
    ms: (a.details && a.details.overallSavingsMs) || 0,
    kb: (a.details && a.details.overallSavingsBytes) ? Math.round(a.details.overallSavingsBytes / 1024) : 0,
    val: a.displayValue || '',
  }))
  .sort((a, b) => b.ms - a.ms || b.kb - a.kb)
  .slice(0, 12);
if (items.length) {
  console.log('  Top failing audits (by est. savings):');
  items.forEach(i => {
    const save = [i.ms ? `~${Math.round(i.ms)}ms` : '', i.kb ? `~${i.kb}KB` : ''].filter(Boolean).join(' ');
    console.log(`    • ${i.title}${save ? '  (' + save + ')' : ''}${i.val ? '  [' + i.val + ']' : ''}`);
  });
}
console.log(`  Reports: ${base}.report.html  |  ${base}.report.json`);
// One-line row for a post-release baseline log (see web-performance.md, Regression gate).
console.log('  ROW| ' + [preset, pct('performance'), pct('accessibility'), pct('best-practices'),
  pct('seo'), m('largest-contentful-paint'), m('total-blocking-time'),
  m('cumulative-layout-shift')].join(' | '));
NODE
}

case "$FORM" in
  desktop) run_one desktop ;;
  mobile)  run_one mobile ;;
  both)    run_one desktop; run_one mobile ;;
  *) echo "form must be desktop|mobile|both (got: $FORM)" >&2; exit 2 ;;
esac
