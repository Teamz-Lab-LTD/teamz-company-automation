#!/usr/bin/env python3
"""
Generic Keyword Planner batch generator — for ANY consumer project.

Turns a project's page inventory into upload-ready CSVs so the user can pull free, exact
Google search volume from Keyword Planner (no API token). Same workflow we proved on
teamzlab-tools, now reusable everywhere the shared automation runs.

  python3 build-keyword-batches.py                       # auto-detect project root + inventory
  python3 build-keyword-batches.py --project-root PATH    # explicit project
  python3 build-keyword-batches.py --sitemap URL_OR_PATH  # force a sitemap source
  python3 build-keyword-batches.py --batch-size 700       # keywords per upload file

Inventory source, in priority order:
  1. <root>/tools.json         (richest — has slugs)
  2. <root>/sitemap.xml        (universal — every SEO site has one)

Output (in the project's own data/ dir, never the submodule):
  data/manual-pull/1-UPLOAD-THESE/batch-NN.csv   header 'Keyword', <=700 rows, <=10 words
  data/manual-pull/2-DROP-RESULTS-HERE/          (created; user drops downloads here)
  data/manual-pull/README.txt                    the loop, written down

Dedupes against anything already pulled in 2-DROP-RESULTS-HERE/ so re-runs only add new work.
SAFE: read-only on the site; writes only its own batch files.
"""
import os, sys, re, csv, json, glob
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO = os.path.dirname(HERE)            # the submodule
sys.path.insert(0, HERE)
from keyword_volume_manual import DEFAULT_TOOL_TYPES, _norm  # reuse the shared vocab

BATCH = 700
MAX_WORDS = 10                          # Planner rejects keywords with >10 words


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def project_root():
    r = arg("--project-root")
    if r:
        return os.path.abspath(r)
    # default: the repo that CONTAINS this submodule (…/<project>/teamz-company-automation)
    cand = os.path.dirname(AUTO)
    return cand


def humanize(slug_or_url):
    """Last path segment -> human phrase. 'us/paycheck-calculator' -> 'paycheck calculator'."""
    p = slug_or_url
    if "://" in p:
        p = urlparse(p).path
    last = p.strip("/").split("/")[-1]
    last = re.sub(r"\.(html?|php|astro|md|mdx)$", "", last)
    return _norm(last.replace("-", " ").replace("_", " "))


def core_of(phrase):
    parts = phrase.split()
    return " ".join(parts[:-1]) if len(parts) > 1 and parts[-1] in DEFAULT_TOOL_TYPES else phrase


def phrases_from_tools_json(path):
    d = json.load(open(path))
    tools = d.get("tools", d if isinstance(d, list) else [])
    out = set()
    for t in tools:
        slug = (t.get("slug") or t.get("path") or t.get("url", "")) if isinstance(t, dict) else str(t)
        if not slug:
            continue
        ph = humanize(slug)
        if ph:
            out.add(ph)
            c = core_of(ph)
            if c != ph:
                out.add(c)
    return out


def phrases_from_sitemap(path_or_url):
    if "://" in path_or_url:
        import urllib.request
        req = urllib.request.Request(path_or_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
        raw = urllib.request.urlopen(req, timeout=30).read()
    else:
        raw = open(path_or_url, "rb").read()
    # strip namespace for easy findall
    text = re.sub(rb'xmlns="[^"]+"', b"", raw)
    root = ET.fromstring(text)
    out = set()
    for loc in root.iter("loc"):
        ph = humanize(loc.text or "")
        if ph:
            out.add(ph)
            c = core_of(ph)
            if c != ph:
                out.add(c)
    return out


def already_pulled(data_dir):
    done = set()
    for f in glob.glob(os.path.join(data_dir, "manual-pull", "2-DROP-RESULTS-HERE", "*.csv")) \
            + glob.glob(os.path.join(data_dir, "manual-pull", "*.csv")):
        try:
            for enc in ("utf-8", "utf-16"):
                try:
                    txt = open(f, encoding=enc).read()
                    if "Keyword" in txt:
                        break
                except Exception:
                    txt = ""
            for r in csv.reader(txt.splitlines(), delimiter="\t"):
                if r and r[0].strip() and r[0].strip() != "Keyword":
                    done.add(_norm(r[0]))
        except Exception:
            continue
    return done


def write_readme(mp):
    open(os.path.join(mp, "README.txt"), "w").write(
        "GOOGLE KEYWORD VOLUME — manual pull (free, no API token)\n"
        "=======================================================\n\n"
        "TWO FOLDERS:\n"
        "  1-UPLOAD-THESE/        <- upload these to Google Keyword Planner, one at a time\n"
        "  2-DROP-RESULTS-HERE/   <- save the downloaded 'historical metrics' .csv here\n\n"
        "LOOP per batch:\n"
        "  1. Google Ads -> Tools -> Keyword Planner -> 'Get search volume and forecasts'\n"
        "  2. blue + -> Upload a file -> 1-UPLOAD-THESE/batch-01.csv -> Submit (Continue past >10-word warnings)\n"
        "  3. 'Saved keywords' tab -> Download -> 'Plan historical metrics' -> .csv\n"
        "  4. move that download into 2-DROP-RESULTS-HERE/\n"
        "  5. keep US as the country for EVERY batch (consistency)\n"
        "  6. re-pull only ~once or twice a year (volume is a 12-month average)\n\n"
        "The engine reads everything in 2-DROP-RESULTS-HERE/ automatically.\n"
        "Templates Google expects: teamz-company-automation/reference/keyword-planner-templates/\n"
    )


def main():
    root = project_root()
    data_dir = os.path.join(root, "data")
    mp = os.path.join(data_dir, "manual-pull")
    up = os.path.join(mp, "1-UPLOAD-THESE")
    os.makedirs(up, exist_ok=True)
    os.makedirs(os.path.join(mp, "2-DROP-RESULTS-HERE"), exist_ok=True)

    src = arg("--sitemap")
    if src:
        phrases = phrases_from_sitemap(src); origin = f"sitemap {src}"
    elif os.path.exists(os.path.join(root, "tools.json")):
        phrases = phrases_from_tools_json(os.path.join(root, "tools.json")); origin = "tools.json"
    elif os.path.exists(os.path.join(root, "sitemap.xml")):
        phrases = phrases_from_sitemap(os.path.join(root, "sitemap.xml")); origin = "sitemap.xml"
    else:
        sys.exit(f"ERROR: no tools.json or sitemap.xml in {root} — pass --sitemap URL_OR_PATH")

    done = already_pulled(data_dir)
    keep = sorted(p for p in phrases
                  if p and len(p) > 2 and len(p.split()) <= MAX_WORDS and p.lower() not in done)

    bs = int(arg("--batch-size", BATCH))
    for f in glob.glob(os.path.join(up, "batch-*.csv")):
        os.remove(f)
    n = 0
    for i in range(0, len(keep), bs):
        n += 1
        with open(os.path.join(up, f"batch-{n:02d}.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["Keyword"])
            for kw in keep[i:i + bs]:
                w.writerow([kw])
    write_readme(mp)

    print(f"  project:        {root}")
    print(f"  inventory:      {origin}  ->  {len(phrases)} phrases")
    print(f"  already pulled: {len(done)}")
    print(f"  NEW to pull:    {len(keep)}  ->  {n} batch file(s) of <= {bs}")
    print(f"  output:         {up}/batch-01.csv ... batch-{n:02d}.csv")
    if n:
        print(f"  NEXT: upload 1-UPLOAD-THESE/batch-01.csv to Keyword Planner (US), "
              f"download historical metrics, drop in 2-DROP-RESULTS-HERE/")
    else:
        print("  nothing new to pull — coverage complete for this project.")


if __name__ == "__main__":
    main()
