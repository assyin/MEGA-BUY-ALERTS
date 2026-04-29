#!/usr/bin/env python3
"""Generate digest and dispatch via Telegram + Email.

Reads from .env:
- TELEGRAM_TOKEN, TELEGRAM_CHAT_ID (existing)
- SMTP_USER (gmail address sending the email)
- SMTP_APP_PASSWORD (Gmail app password — NOT regular password)
- DIGEST_TO_EMAIL (recipient email)
- DIGEST_WINDOW_HOURS (default 8.0)

Usage:
    python3 scripts/send_digest.py [--window-hours N] [--no-telegram] [--no-email]

The HTML report is also written to ../V11_DIGEST_<timestamp>.html for archive.
"""

import argparse
import os
import smtplib
import ssl
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "python" / ".env")

from openclaw.config import get_settings
from supabase import create_client
from digest_report import collect_data, build_markdown, build_html


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    """Send message via Telegram Bot API. Splits if >4000 chars."""
    if not token or not chat_id:
        print("  ⚠️ Telegram skipped (no token/chat_id)", file=sys.stderr)
        return False

    # Telegram limit is 4096 chars per message — split if needed
    chunks = []
    while text:
        if len(text) <= 4000:
            chunks.append(text); break
        # Find a good split point (newline)
        split_at = text.rfind("\n", 0, 4000)
        if split_at < 100: split_at = 4000
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    ok = True
    for i, chunk in enumerate(chunks):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id, "text": chunk, "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    print(f"  ❌ Telegram chunk {i+1}/{len(chunks)} HTTP {resp.status}", file=sys.stderr)
                    ok = False
        except Exception as e:
            print(f"  ❌ Telegram chunk {i+1}/{len(chunks)} failed: {e}", file=sys.stderr)
            ok = False
    if ok:
        print(f"  ✅ Telegram envoyé ({len(chunks)} message{'s' if len(chunks)>1 else ''})", file=sys.stderr)
    return ok


def send_email(smtp_user: str, smtp_pass: str, to_email: str,
               subject: str, html_body: str, plain_body: str) -> bool:
    """Send HTML email via Gmail SMTP (smtp.gmail.com:587 TLS)."""
    if not smtp_user or not smtp_pass:
        print("  ⚠️ Email skipped (SMTP_USER or SMTP_APP_PASSWORD missing in .env)", file=sys.stderr)
        return False
    if not to_email:
        print("  ⚠️ Email skipped (DIGEST_TO_EMAIL missing in .env)", file=sys.stderr)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"  ✅ Email envoyé à {to_email}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  ❌ Email failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=float,
                        default=float(os.getenv("DIGEST_WINDOW_HOURS", "8.0")))
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--archive-dir", default=str(Path(__file__).parent.parent.parent),
                        help="Directory to write archived HTML digest (default: project root)")
    args = parser.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print(f"📥 Collecting V11 data (window={args.window_hours}h)...", file=sys.stderr)
    data = collect_data(sb, args.window_hours)

    md = build_markdown(data)
    html = build_html(data)

    # Archive
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    archive = Path(args.archive_dir) / f"V11_DIGEST_{ts}.html"
    archive.write_text(html, encoding="utf-8")
    print(f"  📂 Archive: {archive}", file=sys.stderr)

    # Subject lines — V11B-centric since c'est notre variant principal
    b = data["variants"]["v11b"]
    bst = b["state"]
    bn = bst.get("total_trades", 0); bw = bst.get("wins", 0)
    bwr = (bw / max(bn, 1)) * 100 if bn else 0
    b_susp = bst.get("is_suspended")
    b_closes = len(b["closes_window"])
    b_pnl = sum((r.get("pnl_usd") or 0) for r in b["closes_window"])

    n_susp_total = sum(1 for v in ('v11a','v11b','v11c','v11d','v11e')
                       if data["variants"][v]["state"].get("is_suspended"))

    if b_susp:
        prefix = "🛑 V11B SUSPENDED"
    elif b_closes > 0:
        prefix = f"📊 V11B WR {bwr:.0f}% • {b_closes} closes ${b_pnl:+,.0f}"
    else:
        prefix = f"📊 V11B WR {bwr:.0f}% • idle"

    if n_susp_total > 0 and not b_susp:
        prefix += f" [+{n_susp_total} other suspended]"

    subject = f"{prefix} — {data['now'].strftime('%Y-%m-%d %H:%M UTC')}"

    if not args.no_telegram:
        send_telegram(s.telegram_token, s.telegram_chat_id, md)

    if not args.no_email:
        send_email(
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_pass=os.getenv("SMTP_APP_PASSWORD", ""),
            to_email=os.getenv("DIGEST_TO_EMAIL", ""),
            subject=subject,
            html_body=html,
            plain_body=md,
        )


if __name__ == "__main__":
    main()
