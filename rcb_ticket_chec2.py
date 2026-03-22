"""
RCB vs SRH Ticket Monitor - RAILWAY 100% ENV VARS
=================================================
ALL credentials via Railway VARIABLES tab ONLY.
No hardcoded secrets.
"""

import os
import requests
import json
import time
import logging
import sys
from datetime import datetime
from bs4 import BeautifulSoup
from twilio.rest import Client

# ── RAILWAY VARIABLES ONLY (NO FALLBACKS) ──
ACCOUNT_SID   = os.getenv('TWILIO_SID')
AUTH_TOKEN    = os.getenv('TWILIO_TOKEN')
CONTENT_SID   = os.getenv('CONTENT_SID')
TO_WHATSAPP   = os.getenv('TO_WHATSAPP')
FROM_WHATSAPP = "whatsapp:+14155238886"  # Fixed Twilio number

# FAIL if vars missing
if not all([ACCOUNT_SID, AUTH_TOKEN, CONTENT_SID, TO_WHATSAPP]):
    print("❌ MISSING RAILWAY VARIABLES! Add to dashboard → VARIABLES tab:")
    print("   TWILIO_SID, TWILIO_TOKEN, CONTENT_SID, TO_WHATSAPP")
    sys.exit(1)

# ── Scraping config ──
TICKET_URLS = [
    "https://shop.royalchallengers.com",
    "https://www.royalchallengers.com"
]
CHECK_EVERY_SEC = 300  # 5 minutes

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

LIVE_SIGNALS = [
    "book now", "buy now", "buy tickets", "book tickets",
    "select seats", "add to cart", "proceed to pay",
]

NOT_LIVE_SIGNALS = [
    "coming soon", "sold out", "not available", "stay tuned",
    "sale not open", "notify me", "ticketgenie"
]

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/rcb_monitor.log"),
    ],
)
log = logging.getLogger(__name__)

def check_tickets() -> tuple[bool, str]:
    """Check RCB pages for live tickets"""
    all_text = ""
    
    for url in TICKET_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=" ").lower()
            all_text += text
            log.info(f"  → {url} ({resp.status_code}) OK")
        except Exception as e:
            log.warning(f"  → {url} ERROR: {e}")
    
    # Block false positives first
    for signal in NOT_LIVE_SIGNALS:
        if signal in all_text:
            return False, f'Blocked: "{signal}"'
    
    # Live signals
    for signal in LIVE_SIGNALS:
        if signal in all_text:
            return True, f'LIVE: "{signal}"'
    
    return False, "No booking signals"

def send_whatsapp():
    """Send WhatsApp alert"""
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    message = client.messages.create(
        from_=FROM_WHATSAPP,
        content_sid=CONTENT_SID,
        content_variables=json.dumps({
            "1": "🚨 RCB vs SRH | Mar 28 | Chinnaswamy",
            "2": "TICKETS LIVE! → shop.royalchallengers.com",
        }),
        to=TO_WHATSAPP,
    )
    log.info(f"✅ WhatsApp sent! SID: {message.sid}")
    return message.sid

def main():
    log.info("=" * 60)
    log.info("  RCB vs SRH Ticket Monitor — RAILWAY 24/7")
    log.info(f"  Pages: {TICKET_URLS}")
    log.info(f"  Check: {CHECK_EVERY_SEC//60} mins")
    log.info(f"  Alert: {TO_WHATSAPP}")
    log.info("=" * 60)

    attempt = 0
    while True:
        attempt += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.info(f"\n[#{attempt}] {now} — checking...")

        is_live, reason = check_tickets()
        status = "LIVE ✅" if is_live else "Not live ❌"
        log.info(f"  Result: {status}  ({reason})")

        if is_live:
            log.info("🎉 TICKETS LIVE! Sending WhatsApp...")
            try:
                sid = send_whatsapp()
                log.info(f"✅ SUCCESS! SID: {sid}")
                log.info("🛑 Stopping — tickets available!")
                break
            except Exception as e:
                log.error(f"❌ WhatsApp failed: {e}")

        log.info(f"  Next: {CHECK_EVERY_SEC//60} mins...\n")
        time.sleep(CHECK_EVERY_SEC)

if __name__ == "__main__":
    main()
