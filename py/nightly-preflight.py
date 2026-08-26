#!/usr/bin/env python3
"""
Nightly preflight — the ONE loud guard that turns silent nightly failures into visible ones.

WHY THIS EXISTS
---------------
A silent-killer audit (2026-07-18) found 27 places the nightly growth engine can fail without a
single error, warning, or log line — the same class of bug that hid 11,201 keywords for months.
The root shape is always the same: **absence of data looks identical to absence of a problem.**
An empty result from a wrong path, a dead token, or a renamed column is indistinguishable from a
legitimate "nothing to do", so the run finishes "successfully" while doing nothing.

This script asserts the invariants those failures violate, and FAILS LOUD when one breaks:
  - a known-non-empty input that comes back empty is a PARSE/CONFIG failure, not a real empty;
  - a resolved repo root that is not the real site root is a path bug (the exemplar);
  - manual-pull CSVs present but 0 keywords parsed means the loader silently dropped them.

It runs per-property (each nightly exports TEAMZ_HOST_SITE_ROOT), so it works for apps, goalkit,
learn AND tools without assuming any one site's shape.

MODES
  nightly-preflight.py --pre      BEFORE any phase. Root/env/input gate. Fail => exit 2 (ABORT run).
  nightly-preflight.py --post     AFTER all phases. Output-artifact gate.  Fail => exit 1 (ALERT).
  nightly-preflight.py --selftest Point at a bogus root; assert it exits non-zero (guards the guard).

REPORTS LOUDLY THREE WAYS (redundant by design)
  1. Nonzero exit — --pre exits 2 (abort), --post exits 1 (alert), internal crash exits 3.
  2. data/preflight-status.json  — {ok, mode, failures:[...], resolved_root, ts}. The morning
     watchdog + build-growth-digest.py read it; a MISSING or STALE preflight-status is itself an
     alert (a preflight that did not run cannot vouch for the night).
  3. osascript notification on failure (best-effort; never the only channel).

THE GUARD ITSELF MUST NEVER FAIL SILENTLY
  - main() is wrapped in try/except BaseException -> full traceback to stderr + a crash status
    file + exit 3. "preflight crashed" and "preflight passed" never look alike.
  - stdlib only, so a broken venv cannot make the guard vanish.
  - --selftest proves the loud-fail path still works, so the guard cannot rot into always-passing.

CONFIG (env; all optional except the root)
  TEAMZ_HOST_SITE_ROOT     the site repo root (the nightly already exports it). REQUIRED.
  TEAMZ_PREFLIGHT_MIN_HTML if set, ROOT must contain >= N built .html files (tools: ~6967; unset
                           on small sites so they are not held to a page floor).
  TEAMZ_PREFLIGHT_TOKENS   comma list of token-file env names to require exist+parse
                           (e.g. TEAMZ_SC_TOKEN_FILE,TEAMZ_GA4_TOKEN_FILE). Default: those two.
  TEAMZ_PREFLIGHT_MAX_AGE_H post-run artifact staleness ceiling in hours (default 30).
"""
import json
import os
import socket
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The automation dir name — the resolved site root must NEVER equal this (that IS the exemplar bug:
# the symlink chain collapsed the root up into teamz-company-automation / teamz-projects).
AUTOMATION_DIRNAME = "teamz-company-automation"


class CheckFail(Exception):
    """A named invariant that did not hold. Carries a human detail for the status file + push."""
    def __init__(self, name, detail):
        super().__init__(f"{name}: {detail}")
        self.name = name
        self.detail = detail


# --------------------------------------------------------------------------- helpers
def _root():
    r = os.environ.get("TEAMZ_HOST_SITE_ROOT")
    if not r:
        raise CheckFail("host-root-unset",
                        "TEAMZ_HOST_SITE_ROOT is not set — the nightly must export it before "
                        "preflight. Without it every path resolves blind.")
    p = Path(r)
    if not p.is_dir():
        raise CheckFail("host-root-missing", f"TEAMZ_HOST_SITE_ROOT={r} is not a directory.")
    return p


def _status_path(root):
    return root / "data" / "preflight-status.json"


def _write_status(root, mode, ok, failures, extra=None):
    """Write the status file. If we cannot even write it, that is itself loud (exit 3 in main)."""
    data = {
        "ok": ok,
        "mode": mode,
        "failures": failures,           # list of {name, detail}
        "resolved_root": str(root) if root else None,
        # ts passed in from the shell (Date.now-free elsewhere, but here we are a real process)
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    if extra:
        data.update(extra)
    p = _status_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def _notify(title, msg):
    """Best-effort Mac notification. NEVER the only channel — the status file + exit code carry it."""
    try:
        import subprocess
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{msg[:180]}" with title "{title[:60]}"'],
            timeout=10, capture_output=True)
    except Exception:
        pass  # a failed notification must not mask the real failure it is announcing


# --------------------------------------------------------------------------- PRE checks
def check_root_is_real(root):
    """The resolved root must be an actual SITE repo, not the automation dir or its parent.
    This one assert catches the entire .resolve()/__file__-math class before any producer runs."""
    if root.name == AUTOMATION_DIRNAME:
        raise CheckFail("root-is-automation-dir",
                        f"resolved root is {root} — that is the automation submodule, not a site "
                        f"root. A path derivation collapsed the symlink chain (the exemplar bug).")
    env = root / ".teamz-automation.env"
    if not env.exists():
        raise CheckFail("root-missing-marker",
                        f"resolved root {root} has no .teamz-automation.env — it is almost "
                        f"certainly the wrong directory (every site root has this file).")


def check_manual_volume_coverage(root):
    """If manual-pull result CSVs exist, the loader MUST parse >0 keywords. Empty-with-input is a
    parse failure (renamed Planner column / bad encoding), NOT a legitimate empty — the exact
    mechanism that lost 11,201 keywords."""
    data = root / "data"
    csvs = list((data / "manual-pull").rglob("*.csv")) if (data / "manual-pull").exists() else []
    # also the top-level back-compat location the loader reads
    csvs += list(data.glob("*.csv"))
    if not csvs:
        return  # no batches pulled yet — a genuine, legitimate empty. Nothing to assert.
    sys.path.insert(0, str(HERE))
    try:
        from keyword_volume_manual import load_manual_volume
    except Exception as e:
        raise CheckFail("kwvol-import-failed",
                        f"cannot import keyword_volume_manual to verify {len(csvs)} CSVs: {e}")
    mv = load_manual_volume(str(data))
    have = sum(1 for v in mv.values() if v.get("vol") is not None)
    if have == 0:
        raise CheckFail("kwvol-parsed-zero",
                        f"{len(csvs)} Planner CSV(s) present but load_manual_volume parsed 0 "
                        f"keywords with volume — header renamed or encoding changed. Real demand "
                        f"is being silently dropped (this is the original 11k-keyword bug).")


def check_min_html(root):
    """Optional page floor (tools sets it). Catches a producer that would scan 0 pages."""
    n = os.environ.get("TEAMZ_PREFLIGHT_MIN_HTML")
    if not n:
        return
    try:
        floor = int(n)
    except ValueError:
        raise CheckFail("min-html-misconfig", f"TEAMZ_PREFLIGHT_MIN_HTML={n!r} is not an int.")
    skip = {"node_modules", ".git", ".astro"}
    count = 0
    for p in root.rglob("*.html"):
        if skip & set(p.parts):
            continue
        count += 1
        if count >= floor:
            return
    raise CheckFail("min-html-floor",
                    f"found only {count} .html under {root} (floor {floor}). Either the root "
                    f"resolved wrong or a producer emitted nothing.")


def check_tokens_present(root):
    """Configured auth tokens must exist and parse. A deleted/empty token file is a silent
    'signal absent' otherwise. (A live 200-probe is intentionally NOT done here — a transient
    network blip must not abort the whole night; dead-token-at-runtime is surfaced by the API
    fetchers' sentinels, not by aborting.)"""
    names = os.environ.get("TEAMZ_PREFLIGHT_TOKENS", "TEAMZ_SC_TOKEN_FILE,TEAMZ_GA4_TOKEN_FILE")
    for env_name in [x.strip() for x in names.split(",") if x.strip()]:
        path = os.environ.get(env_name)
        if not path:
            continue  # this property does not configure that token — fine
        path = os.path.expandvars(os.path.expanduser(path))
        f = Path(path)
        if not f.exists():
            raise CheckFail("token-missing",
                            f"{env_name} -> {path} does not exist. Auth will silently return "
                            f"empty, dropping that site's strongest signal.")
        try:
            json.loads(f.read_text())
        except Exception as e:
            raise CheckFail("token-unparseable", f"{env_name} -> {path} is not valid JSON: {e}")


# --------------------------------------------------------------------------- POST checks
def check_content_queue_parses(root):
    """If the content brain wrote a queue tonight, it must be valid JSON. A truncated/half-written
    queue that the agent then reads is a silent mis-build."""
    q = root / "data" / "content-queue.json"
    if not q.exists():
        return  # tools uses enhance-queue.json; a missing content-queue is legitimate there
    try:
        json.loads(q.read_text())
    except Exception as e:
        raise CheckFail("content-queue-corrupt",
                        f"data/content-queue.json did not parse ({e}) — the content agent may "
                        f"have built off a broken queue.")


def check_status_freshness(root):
    """The runner writes nightly-status.json at EXIT (after this --post in the trap, so we cannot
    read tonight's yet). What we CAN catch: a status file frozen from many days ago means the
    runner has not completed a clean pass in a long time."""
    s = root / "data" / "nightly-status.json"
    if not s.exists():
        return  # first ever run
    try:
        max_age = float(os.environ.get("TEAMZ_PREFLIGHT_MAX_AGE_H", "30"))
    except ValueError:
        max_age = 30.0
    age_h = (datetime.now() - datetime.fromtimestamp(s.stat().st_mtime)).total_seconds() / 3600.0
    # 3 nights of no completed run: the trap should rewrite this every night, so >72h means the
    # runner is dying before EXIT or not being scheduled at all.
    if age_h > max(max_age, 72):
        raise CheckFail("status-frozen",
                        f"data/nightly-status.json is {age_h:.0f}h old — the nightly has not "
                        f"completed a run in days (crashing before its EXIT trap, or not firing).")


def check_shared_env_contracts(root):
    """Every consumer of a shared env var must agree on what its value means.

    This exists because of a real two-night outage on goalkit, 2026-08-14..16.
    TEAMZ_KW_GEO was set to "2050" to fix build-keyword-volume.py, which wants a
    numeric Google Ads geoTargetConstant. Two OTHER scripts read the same variable
    and wanted a country NAME:

        build-keyword-volume-auto.py   -> "2050" not in its name->id dict
        build-keyword-candidates.py    -> wrote "SET LOCATION = 2050" for a human

    build-keyword-volume-auto.py printed "refusing to guess" and returned 0, so the
    nightly recorded success while goalkit's pending Keyword Planner batches were
    never resolved. Nothing shouted for two nights.

    The lesson is not "remember to grep before changing config" — that is a promise,
    not a guard. The guard is: validate the value against the SHARED resolver before
    the night runs, and abort loudly if no consumer can use it. A config value that
    no script understands must never reach a phase that will quietly skip itself.
    """
    geo = os.getenv("TEAMZ_KW_GEO")
    if not geo:
        return  # unset is legal — every reader has its own documented default
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import _teamz_geo
    except ImportError as e:
        raise CheckFail("geo-resolver-missing",
                        f"TEAMZ_KW_GEO={geo!r} is set but _teamz_geo.py could not be "
                        f"imported ({e}) — the scripts that read it cannot agree on its "
                        f"meaning.")
    gid, name = _teamz_geo.resolve(geo)
    if not gid:
        raise CheckFail(
            "kw-geo-unresolvable",
            f"TEAMZ_KW_GEO={geo!r} resolves to nothing. build-keyword-volume-auto.py "
            f"will refuse to price any keyword batch and STILL exit 0, so the night "
            f"would look clean while keyword data silently stops updating. Add it to "
            f"_teamz_geo.py (ID_TO_NAME / NAME_TO_ID / CODE_TO_ID) or unset it.")


# --------------------------------------------------------------------------- runners
def check_dns_was_available(root):
    """Did name resolution work DURING the run?

    2026-08-26: the router at 192.168.0.1 was the machine's only resolver, it stopped answering
    for the whole 21:00-22:05 window, and every outbound call failed with
    `[Errno 8] nodename nor servname provided`. That surfaced as THIRTEEN separate health alerts
    — GSC token refresh, football-data.org credentials, the Sleeper NFL feed, git push, the
    fortress, anomalies, broken pages, marooned pages, geo value, ideas brief, and more — each
    reading like its own bug. Three nights were spent that way. One outage should report as one
    outage, and a night that could not reach the network must read as UNKNOWN, never as healthy.

    Checked after the run, not before: aborting the night on a blip at 21:00 would throw away a
    build that DNS recovery two minutes later would have completed. So this looks for evidence in
    what actually happened, and also probes now so a still-broken resolver is named as current.
    """
    marks = ("[Errno 8] nodename nor servname", "NameResolutionError",
             "Failed to resolve", "Temporary failure in name resolution")
    logs = sorted(Path(root).glob("logs/*nightly*.log"), key=lambda f: f.stat().st_mtime)
    hits, scanned, scope = 0, None, "no nightly log found"
    if logs:
        try:
            lines = logs[-1].read_text(errors="replace").splitlines()
        except OSError as e:
            raise CheckFail("dns-unreadable-log",
                            f"could not read {logs[-1].name} ({e}) — cannot tell whether the "
                            f"network worked tonight. Treat tonight's network results as UNKNOWN.")
        # Only THIS run. Scanning the whole file would re-report every past outage forever, which
        # is how an alert section teaches its reader to skip it.
        start = 0
        for i in range(len(lines) - 1, -1, -1):
            if "NIGHTLY BUILD —" in lines[i] or "NIGHTLY:" in lines[i] or "=== Phase 1" in lines[i]:
                start = i
                break
        scope = (f"{logs[-1].name} from its last run marker"
                 if start else f"{logs[-1].name} (no run marker found — scanned whole file)")
        window = lines[start:]
        scanned = len(window)
        hits = sum(1 for ln in window if any(m in ln for m in marks))

    now_ok = True
    try:
        socket.getaddrinfo("oauth2.googleapis.com", 443)
    except OSError:
        now_ok = False

    if not now_ok:
        raise CheckFail("dns-down-now",
                        "name resolution is failing RIGHT NOW (oauth2.googleapis.com). Every "
                        "network-dependent result in this run is UNKNOWN, not healthy — the "
                        "tokens, feeds and push did not fail one by one, they all failed for "
                        "this one reason. Check the router/DNS before reading any other alert.")
    if hits:
        raise CheckFail("dns-failed-during-run",
                        f"{hits} name-resolution failure(s) in {scope} ({scanned} lines). DNS "
                        f"works again now, so the other network alerts from this run are "
                        f"symptoms of that outage, not {hits} separate faults. Anything fetched "
                        f"over the network tonight is UNKNOWN, not confirmed healthy.")


PRE = [check_root_is_real, check_manual_volume_coverage, check_min_html, check_tokens_present,
       check_shared_env_contracts]
POST = [check_content_queue_parses, check_status_freshness, check_dns_was_available]


def _run(mode, checks, abort_code):
    root = _root()  # raises CheckFail if unset/missing — caught below
    failures = []
    for chk in checks:
        try:
            chk(root)
        except CheckFail as cf:
            failures.append({"name": cf.name, "detail": cf.detail})
        # A check raising anything OTHER than CheckFail is a bug in the check itself — surface it
        # loudly rather than swallow (that would be the very sin we are guarding against).
        except Exception as e:  # noqa: BLE001
            failures.append({"name": f"{chk.__name__}-crashed",
                             "detail": f"{type(e).__name__}: {e}"})
    ok = not failures
    _write_status(root, mode, ok, failures)
    if ok:
        print(f"  preflight {mode}: OK ({len(checks)} checks, root={root.name})")
        return 0
    print(f"  preflight {mode}: FAILED ({len(failures)}/{len(checks)}):", file=sys.stderr)
    for f in failures:
        print(f"    ✗ {f['name']}: {f['detail']}", file=sys.stderr)
    _notify(f"NIGHTLY {mode.upper()} FAILED — {root.name}",
            "; ".join(f["name"] for f in failures))
    return abort_code


def _selftest():
    """Prove the loud-fail path works: a bogus root MUST make --pre exit non-zero. If this ever
    passes-when-it-should-fail, the guard has rotted and this exits 1 to fail CI."""
    saved = os.environ.get("TEAMZ_HOST_SITE_ROOT")
    try:
        os.environ["TEAMZ_HOST_SITE_ROOT"] = "/nonexistent/bogus/root/for/selftest"
        try:
            code = _run("pre", PRE, 2)
        except CheckFail:
            code = 2  # _root() itself raising is also a correct loud fail
        if code == 0:
            print("  SELFTEST FAILED: bogus root did not trip preflight — the guard is broken.",
                  file=sys.stderr)
            return 1
        print("  selftest OK: bogus root correctly tripped the guard (exit != 0).")
        return 0
    finally:
        if saved is None:
            os.environ.pop("TEAMZ_HOST_SITE_ROOT", None)
        else:
            os.environ["TEAMZ_HOST_SITE_ROOT"] = saved


def main():
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return _selftest()
    if "--pre" in argv:
        return _run("pre", PRE, 2)     # exit 2 => ABORT the run
    if "--post" in argv:
        return _run("post", POST, 1)   # exit 1 => ALERT, run already happened
    print("usage: nightly-preflight.py [--pre | --post | --selftest]", file=sys.stderr)
    return 64


if __name__ == "__main__":
    # NOTE: main() RETURNS an int and never calls sys.exit itself, so the except BaseException
    # below only ever catches a genuine internal crash — never our own SystemExit. The real exit
    # code is set by the `else` branch.
    try:
        _rc = main()
    except CheckFail as cf:
        # A pre-flight precondition (e.g. root unset) failed before we could run checks. Still loud.
        try:
            r = os.environ.get("TEAMZ_HOST_SITE_ROOT")
            root = Path(r) if r and Path(r).is_dir() else None
            if root:
                _write_status(root, "pre", False, [{"name": cf.name, "detail": cf.detail}])
        except Exception:
            pass
        print(f"  preflight ABORT: {cf.name}: {cf.detail}", file=sys.stderr)
        _notify("NIGHTLY PREFLIGHT ABORT", f"{cf.name}: {cf.detail}")
        sys.exit(2)
    except BaseException as e:  # noqa: BLE001 — the guard must never die quietly
        traceback.print_exc()
        try:
            r = os.environ.get("TEAMZ_HOST_SITE_ROOT")
            root = Path(r) if r and Path(r).is_dir() else None
            if root:
                _write_status(root, "crash", False,
                              [{"name": "preflight-crashed", "detail": f"{type(e).__name__}: {e}"}])
        except Exception:
            pass
        _notify("NIGHTLY PREFLIGHT CRASHED", f"{type(e).__name__}: {e}")
        sys.exit(3)
    else:
        sys.exit(_rc)
