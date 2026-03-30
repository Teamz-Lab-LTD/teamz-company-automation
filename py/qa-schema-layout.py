#!/usr/bin/env python3
"""
Validate schema/layout consistency for Teamz Lab tool pages.

Checks:
- Duplicate FAQPage or WebApplication schema blocks in source HTML
- renderFAQs() without a #tool-faqs container
- renderRelatedTools() without a #related-tools container
- Redundant injectFAQSchema()/injectWebAppSchema() calls when static schema exists

Usage:
  python3 scripts/qa-schema-layout.py
  python3 scripts/qa-schema-layout.py --file tools/birthday-invitation-maker/index.html
  python3 scripts/qa-schema-layout.py --url https://tool.teamzlab.com/tools/birthday-invitation-maker/
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from _teamz_config import load_runtime

RUNTIME = load_runtime(__file__)
REPO_ROOT = Path(RUNTIME["host_site_root"])
PROJECT_TYPE = RUNTIME.get("project_type", "website")


@dataclass
class PageReport:
    label: str
    ldjson_count: int
    faq_count: int
    webapp_count: int
    breadcrumb_count: int
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _read_local(path_str: str) -> tuple[str, str]:
    path = Path(path_str)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return str(path.relative_to(REPO_ROOT)), path.read_text(encoding="utf-8", errors="ignore")


def _read_url(url: str) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "TeamzLab-QA/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read().decode(charset, errors="ignore")
    return url, html


def _inspect(label: str, html: str) -> PageReport:
    report = PageReport(
        label=label,
        ldjson_count=html.count('application/ld+json'),
        faq_count=html.count('"@type": "FAQPage"'),
        webapp_count=html.count('"@type": "WebApplication"'),
        breadcrumb_count=html.count('"@type": "BreadcrumbList"'),
    )

    has_faq_container = 'id="tool-faqs"' in html
    has_related_container = 'id="related-tools"' in html
    calls_render_faqs = "renderFAQs(" in html
    calls_render_related = "renderRelatedTools(" in html
    calls_inject_faq = "injectFAQSchema(" in html
    calls_inject_webapp = "injectWebAppSchema(" in html

    if report.faq_count > 1:
        report.issues.append(f"Duplicate FAQPage schema blocks in source ({report.faq_count}x)")
    if report.webapp_count > 1:
        report.issues.append(f"Duplicate WebApplication schema blocks in source ({report.webapp_count}x)")
    if calls_render_faqs and not has_faq_container:
        report.issues.append("Calls renderFAQs() but page is missing #tool-faqs")
    if calls_render_related and not has_related_container:
        report.issues.append("Calls renderRelatedTools() but page is missing #related-tools")

    if calls_inject_faq and report.faq_count >= 1:
        report.warnings.append("Calls injectFAQSchema() even though static FAQPage schema already exists")
    if calls_inject_webapp and report.webapp_count >= 1:
        report.warnings.append("Calls injectWebAppSchema() even though static WebApplication schema already exists")

    return report


def _scan_repo() -> list[PageReport]:
    reports: list[PageReport] = []
    for path in sorted(REPO_ROOT.glob("**/index.html")):
        rel = str(path.relative_to(REPO_ROOT))
        if rel.startswith(".git/"):
            continue
        reports.append(_inspect(rel, path.read_text(encoding="utf-8", errors="ignore")))
    return reports


def _print_single(report: PageReport) -> int:
    print(f"Page: {report.label}")
    print(f"  JSON-LD blocks:   {report.ldjson_count}")
    print(f"  FAQPage blocks:   {report.faq_count}")
    print(f"  WebApp blocks:    {report.webapp_count}")
    print(f"  Breadcrumb blocks:{report.breadcrumb_count}")

    if report.issues:
        print("  Errors:")
        for issue in report.issues:
            print(f"    - {issue}")
    else:
        print("  Errors: none")

    if report.warnings:
        print("  Warnings:")
        for warning in report.warnings:
            print(f"    - {warning}")
    else:
        print("  Warnings: none")

    return 1 if report.issues else 0


def _print_repo_summary(reports: list[PageReport], show_examples: int) -> int:
    issue_pages = [r for r in reports if r.issues]
    warning_pages = [r for r in reports if r.warnings]
    issue_counter: Counter[str] = Counter()
    warning_counter: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)

    for report in reports:
        for issue in report.issues:
            issue_counter[issue] += 1
            if len(examples[issue]) < show_examples:
                examples[issue].append(report.label)
        for warning in report.warnings:
            warning_counter[warning] += 1

    print("============================================")
    print("  Teamz Lab Schema/Layout QA")
    print("============================================")
    print(f"  Pages scanned:    {len(reports)}")
    print(f"  Error pages:      {len(issue_pages)}")
    print(f"  Warning pages:    {len(warning_pages)}")
    print("")

    if issue_counter:
        print("  Errors:")
        for issue, count in issue_counter.most_common():
            print(f"    - {issue}: {count}")
            for sample in examples[issue]:
                print(f"      • {sample}")
    else:
        print("  Errors: none")

    if warning_counter:
        print("")
        print("  Warnings:")
        for warning, count in warning_counter.most_common():
            print(f"    - {warning}: {count}")

    return 1 if issue_pages else 0


def main() -> int:
    if PROJECT_TYPE == "app":
        print("INFO: qa-schema-layout.py is website-focused and disabled for TEAMZ_PROJECT_TYPE=app.")
        return 2

    parser = argparse.ArgumentParser(description="Validate schema/layout consistency for Teamz Lab pages.")
    parser.add_argument("--file", help="Local file to inspect, relative to repo root or absolute path.")
    parser.add_argument("--url", help="Live URL to inspect.")
    parser.add_argument("--examples", type=int, default=8, help="How many example pages to show per issue in repo mode.")
    args = parser.parse_args()

    try:
        if args.file and args.url:
            parser.error("Use either --file or --url, not both.")
        if args.file:
            label, html = _read_local(args.file)
            return _print_single(_inspect(label, html))
        if args.url:
            label, html = _read_url(args.url)
            return _print_single(_inspect(label, html))
        return _print_repo_summary(_scan_repo(), args.examples)
    except FileNotFoundError as exc:
        print(f"File not found: {exc}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"URL fetch failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
