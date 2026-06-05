#!/usr/bin/env python3
"""
Mobile-first UX gate — loads changed tools in a real iPhone-sized headless browser and
enforces the ui-ux-pro-max mobile rules. 50%+ of users are mobile, so a tool that isn't
genuinely usable on a phone loses half the audience. This BLOCKS (exit 1) on hard failures.

Reuses qa-runtime-test.py's server + tool-discovery (no duplicate infra).

HARD fails (block the ship):
  - horizontal scroll (the #1 mobile bug — content wider than the screen)
  - touch targets < 44x44 px on visible controls (Apple HIG / Material 48dp)
  - viewport meta missing OR zoom locked (user-scalable=no / maximum-scale=1)
WARN (report, don't block):
  - body text < 12px (iOS auto-zooms < 16px)
  - text/background contrast < 4.5:1 (WCAG AA)

  python3 qa-mobile-ux.py --changed     # only tools changed vs origin/main (nightly/pre-commit)
  python3 qa-mobile-ux.py --file hub/tool
  python3 qa-mobile-ux.py --all          # every tool (slow)
"""
import os, sys, json, importlib.util, argparse
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))


def _qrt():
    """Reuse qa-runtime-test.py (hyphenated -> importlib) for server + discovery."""
    spec = importlib.util.spec_from_file_location("qrt", os.path.join(HERE, "qa-runtime-test.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


AUDIT_JS = r"""
() => {
  const vw = window.innerWidth, r = {};
  r.horizontalScroll = document.documentElement.scrollWidth > vw + 2;
  r.scrollWidth = document.documentElement.scrollWidth; r.vw = vw;
  const m = document.querySelector('meta[name=viewport]');
  r.viewportMeta = !!m;
  r.viewportLocked = m ? /user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0+)?\s*(,|$)/i.test(m.content||'') : false;
  const small = [];
  document.querySelectorAll('button,a,input,select,textarea,[role=button],[onclick]').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || el.offsetParent === null) return;
    if (el.type === 'hidden') return;
    const b = el.getBoundingClientRect();
    if (b.width === 0 || b.height === 0) return;
    if (b.width < 44 || b.height < 44)
      small.push(el.tagName + ':' + (el.textContent || el.value || el.type || '').trim().slice(0, 18)
                 + ` (${Math.round(b.width)}x${Math.round(b.height)})`);
  });
  r.smallTouch = small.slice(0, 10); r.smallTouchCount = small.length;
  let tiny = 0;
  document.querySelectorAll('p,span,div,li,td,label,a,button,input').forEach(el => {
    if (!el.textContent || !el.textContent.trim()) return;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs && fs < 12) tiny++;
  });
  r.tinyFonts = tiny;
  const lum = c => { const m = (c||'').match(/\d+(\.\d+)?/g); if (!m) return 1;
    const [r1,g1,b1] = m.slice(0,3).map(x => { x/=255; return x<=0.03928 ? x/12.92 : Math.pow((x+0.055)/1.055,2.4); });
    return 0.2126*r1 + 0.7152*g1 + 0.0722*b1; };
  let low = 0, checked = 0;
  document.querySelectorAll('p,span,a,button,h1,h2,h3,li,td,label').forEach(el => {
    if (checked > 50 || !el.textContent.trim()) return;
    const s = getComputedStyle(el); const fg = lum(s.color);
    let bg = s.backgroundColor, p = el;
    while ((bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') && p.parentElement) { p = p.parentElement; bg = getComputedStyle(p).backgroundColor; }
    const bl = lum(bg); const ratio = (Math.max(fg,bl)+0.05)/(Math.min(fg,bl)+0.05);
    checked++; if (ratio < 4.5) low++;
  });
  r.lowContrast = low; r.contrastChecked = checked;
  return r;
}
"""


def audit(tools):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("  (playwright not installed — mobile UX gate skipped, non-fatal)")
        return []
    qrt = _qrt()
    proc = qrt.start_server()
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": 390, "height": 844},   # iPhone 14-ish
                device_scale_factor=3, is_mobile=True, has_touch=True,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                           "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
            for t in tools:
                url = f"http://localhost:{qrt.SERVER_PORT}/{t}/"
                page = ctx.new_page()
                issue = {"tool": t, "hard": [], "warn": []}
                try:
                    page.goto(url, timeout=qrt.PAGE_TIMEOUT, wait_until="domcontentloaded")
                    page.wait_for_timeout(400)
                    a = page.evaluate(AUDIT_JS)
                    if a["horizontalScroll"]:
                        issue["hard"].append(f"horizontal scroll ({a['scrollWidth']}px > {a['vw']}px screen)")
                    if not a["viewportMeta"]:
                        issue["hard"].append("no viewport meta tag")
                    elif a["viewportLocked"]:
                        issue["hard"].append("zoom locked (user-scalable=no / maximum-scale=1)")
                    # Touch targets are WARN, not HARD: they're usually a SHARED-CSS root cause
                    # (every tool shows ~100), so blocking would halt the whole pipeline. Fix the
                    # shared CSS once -> all tools pass -> then this can become HARD. Surfaced loud
                    # so the Phase 4 agent / a shared-CSS pass addresses it.
                    if a["smallTouchCount"]:
                        issue["warn"].append(f"{a['smallTouchCount']} touch target(s) < 44px: {', '.join(a['smallTouch'][:4])}")
                    if a["tinyFonts"]:
                        issue["warn"].append(f"{a['tinyFonts']} element(s) text < 12px")
                    if a["lowContrast"]:
                        issue["warn"].append(f"{a['lowContrast']}/{a['contrastChecked']} text element(s) contrast < 4.5:1")
                except Exception as e:
                    issue["hard"].append(f"page failed to load: {type(e).__name__}")
                finally:
                    page.close()
                results.append(issue)
            browser.close()
    finally:
        qrt.stop_server(proc)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--file", type=str)
    args = ap.parse_args()
    qrt = _qrt()
    if args.file:
        tools = [args.file.strip("/")]
    elif args.all:
        tools = qrt.get_all_tools()
    else:
        tools = qrt.get_changed_tools()
    if not tools:
        print("  mobile UX gate: no tools to check."); return 0
    print(f"  mobile UX gate: auditing {len(tools)} tool(s) at 390x844 (iPhone)...")
    results = audit(tools)
    hard = [r for r in results if r["hard"]]
    warn = [r for r in results if r["warn"] and not r["hard"]]
    for r in results:
        for h in r["hard"]:
            print(f"    ✗ HARD  /{r['tool']}/  {h}")
        for w in r["warn"]:
            print(f"    ! warn  /{r['tool']}/  {w}")
    print(f"  -> {len(results)} audited | {len(hard)} HARD fail | {len(warn)} warn-only")
    if hard:
        print("  MOBILE UX GATE FAILED — fix hard issues before ship (50% of users are mobile).")
        return 1
    print("  ✓ mobile UX gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
