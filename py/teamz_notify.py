#!/usr/bin/env python3
"""
teamz_notify — one place every Teamz Lab monitor reaches the owner from.

WHY THIS EXISTS. The WhatsApp and email senders were written well, and then
lived inside build-crashlytics-monitor.py where only crash alerts could use
them. Everything else fell back to `osascript display notification` — a
popup on a Mac at home. The owner drives Uber. A monitor that can only
reach a machine nobody is sitting at has not reported anything.

Measured cost of that: growth-watchdog correctly caught apps' dirty-tree
lock on 2026-07-26, 07-27, 08-01, 08-02 and 08-04, and goalkit/learn push
failures on 08-03 and 08-04. Every one fired a macOS popup into an empty
room. The owner found out on 2026-08-06 by asking a question.

CHANNELS, in the order dispatch() tries them:
  whatsapp  CallMeBot relay. Needs ~/.config/teamzlab/whatsapp-callmebot.env
  email     SMTP. Needs ~/.config/teamzlab/smtp.env (Gmail App Password)
  macos     osascript. Always available on darwin; last resort, not a plan.

Both env files ship as .example only — they hold credentials the owner has
to create (a WhatsApp handshake from his own number, or a Gmail App
Password). Until one is filled in, dispatch() degrades to the macOS popup
and SAYS SO on every line it prints.

DESIGN RULES, all learned the hard way here:
  * A notifier must never crash its caller. Every sender catches broadly and
    returns (ok, detail) — a monitor that dies while reporting is worse than
    one that stays quiet.
  * "not configured" and "failed to send" must never look alike. Silence has
    to be distinguishable from breakage, or the next outage reads as calm.
  * dispatch() returns what actually happened so a caller can record it.
    A caller that assumes delivery is the same bug one layer up.
"""
from __future__ import annotations

import smtplib
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "teamzlab"
WHATSAPP_ENV = CONFIG_DIR / "whatsapp-callmebot.env"
SMTP_ENV = CONFIG_DIR / "smtp.env"


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a trivial KEY=VALUE env file. Missing file -> {}."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def notify_whatsapp(text: str) -> tuple[bool, str]:
    cfg = load_env_file(WHATSAPP_ENV)
    phone, key = cfg.get("CALLMEBOT_PHONE"), cfg.get("CALLMEBOT_APIKEY")
    if not phone or not key:
        return False, f"not configured ({WHATSAPP_ENV})"
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
        {"phone": phone, "text": text[:900], "apikey": key}
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return (r.status == 200), f"HTTP {r.status}"
    except Exception as e:  # noqa: BLE001 - notification must never crash the caller
        return False, str(e)[:120]


def notify_email(subject: str, text: str) -> tuple[bool, str]:
    cfg = load_env_file(SMTP_ENV)
    required = ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_EMAIL_TO")
    if not all(cfg.get(k) for k in required):
        return False, f"not configured ({SMTP_ENV})"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["SMTP_USER"]
    msg["To"] = cfg["ALERT_EMAIL_TO"]
    msg.set_content(text)
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], int(cfg.get("SMTP_PORT", 587)), timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
            s.send_message(msg)
        return True, "sent"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:120]


def notify_macos(text: str, title: str = "Teamz Lab") -> tuple[bool, str]:
    if sys.platform != "darwin":
        return False, "not macOS"
    first = text.splitlines()[0][:180].replace('"', "'") if text.strip() else title
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{first}" with title "{title}"'],
            capture_output=True, timeout=15,
        )
        return True, "shown"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:80]


def dispatch(subject: str, text: str, title: str = "Teamz Lab",
             log=print) -> dict[str, tuple[bool, str]]:
    """Send `text` down every configured channel. Returns {channel: (ok, detail)}.

    Never raises. Prints one line per channel so "skipped — not configured"
    and "skipped — SMTPAuthenticationError" are visibly different states.

    Callers should look at the result: if nothing but macos succeeded, the
    alert did NOT leave the machine, and saying otherwise is the exact class
    of lie this module exists to stop.
    """
    results: dict[str, tuple[bool, str]] = {}
    for name, fn in (
        ("whatsapp", lambda: notify_whatsapp(text)),
        ("email", lambda: notify_email(subject, text)),
        ("macos", lambda: notify_macos(text, title)),
    ):
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001 - belt and braces
            ok, detail = False, f"{type(e).__name__}: {str(e)[:80]}"
        results[name] = (ok, detail)
        log(f"  notify/{name:<9} {'sent' if ok else 'skipped'} — {detail}")
    return results


def reached_owner(results: dict[str, tuple[bool, str]]) -> bool:
    """True only if a channel that reaches the owner AWAY from the Mac worked."""
    return any(ok for ch, (ok, _) in results.items() if ch in ("whatsapp", "email"))
