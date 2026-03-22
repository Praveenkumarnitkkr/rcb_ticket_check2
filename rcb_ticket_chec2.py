"""
RCB vs SRH Ticket Monitor
==========================
Checks shop.royalchallengers.com/ticket every 5 minutes.
Sends a WhatsApp via Twilio the moment tickets go live.

Install:
    pip install requests beautifulsoup4 twilio

Run:
    python rcb_ticket_monitor.py
"""

import requests
import json
import time
import logging
import sys
from datetime import datetime
from bs4 import BeautifulSoup
from twilio.rest import Client

# ── Twilio config ──────────────────────────────────────────────────────────────
ACCOUNT_SID   = "AC3c49ee35d2954cb360c26675339002c0"
AUTH_TOKEN    = "c73040cf206d29f552e3f994bf06e642"
CONTENT_SID   = "HXb5b62575e6e4ff6129ad7c8efe1f983e"
FROM_WHATSAPP = "whatsapp:+14155238886"
TO_WHATSAPP   = "whatsapp:+918529372603"

# ── Scraping config ────────────────────────────────────────────────────────────
TICKET_URL      = "https://shop.royalchallengers.com/ticket"
CHECK_EVERY_SEC = 300   # 5 minutes

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

# Words that mean tickets ARE available
LIVE_SIGNALS = [
    "book now", "buy now", "buy tickets", "book tickets",
    "select seats", "add to cart", "proceed to pay",
    "get tickets", "purchase", "book your seats",
]

# Words that mean tickets are NOT open yet
NOT_LIVE_SIGNALS = [
    "coming soon", "sold out", "not available", "stay tuned",
    "sale not open", "notify me", "nginx",   # nginx = blank server page = not live
]

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("rcb_monitor.log"),
    ],
)
log = logging.getLogger(__name__)


# ── Core check ─────────────────────────────────────────────────────────────────
def check_tickets() -> tuple[bool, str]:
    """
    Fetch the RCB ticket page and decide if tickets are live.
    Returns (is_live: bool, reason: str)
    """
    try:
        resp = requests.get(TICKET_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return False, f"Fetch error: {e}"

    text = BeautifulSoup(resp.text, "html.parser").get_text(separator=" ").lower()

    # Check NOT-live signals first (higher priority)
    for signal in NOT_LIVE_SIGNALS:
        if signal in text:
            return False, f'Page contains "{signal}"'

    # Check live signals
    for signal in LIVE_SIGNALS:
        if signal in text:
            return True, f'Page contains "{signal}"'

    return False, "No booking signals found on page"


# ── WhatsApp alert ─────────────────────────────────────────────────────────────
def send_whatsapp():
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    message = client.messages.create(
        from_=FROM_WHATSAPP,
        content_sid=CONTENT_SID,
        content_variables=json.dumps({
            "1": "RCB vs SRH | Mar 28 | Chinnaswamy",
            "2": "Tickets LIVE! Book now: shop.royalchallengers.com/ticket",
        }),
        to=TO_WHATSAPP,
    )
    log.info(f"WhatsApp sent! SID: {message.sid}")
    return message.sid


# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 55)
    log.info("  RCB vs SRH Ticket Monitor — Started")
    log.info(f"  Watching : {TICKET_URL}")
    log.info(f"  Interval : every {CHECK_EVERY_SEC // 60} minutes")
    log.info(f"  Alert to : {TO_WHATSAPP}")
    log.info("=" * 55)

    attempt = 0
    while True:
        attempt += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.info(f"[#{attempt}] {now} — checking...")

        is_live, reason = check_tickets()
        log.info(f"  Result : {'LIVE ✅' if is_live else 'Not live ❌'}  ({reason})")

        if is_live:
            log.info("  Sending WhatsApp alert...")
            try:
                sid = send_whatsapp()
                log.info(f"  Done. SID: {sid}")
                log.info("  Monitor stopping — tickets are live!")
                break
            except Exception as e:
                log.error(f"  WhatsApp failed: {e} — will retry next check.")

        print(f"✅ Script running fine | Check #{attempt} at {now} | Tickets not live yet | Next check in {CHECK_EVERY_SEC // 60} min...")
        log.info(f"  Next check in {CHECK_EVERY_SEC // 60} min...\n")
        time.sleep(CHECK_EVERY_SEC)


if __name__ == "__main__":
    main()
