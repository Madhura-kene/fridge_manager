"""
telegram_bot.py
Telegram Bot API helpers, message builders, and APScheduler evening reminder.
Imported by web_app.py for the Telegram tab.

Setup:
  1. Copy .env.example → .env
  2. Message @BotFather on Telegram → /newbot → copy token → paste into .env
  3. Start your bot, visit:
     https://api.telegram.org/bot<TOKEN>/getUpdates
  4. Copy the "id" value → paste TELEGRAM_CHAT_ID in .env
"""

import os
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()   # reads .env in the project root
except ImportError:
    pass  # python-dotenv is optional; export env vars manually if not installed

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

from inventory import get_restock_list, get_expiring_items, days_until_expiry

# ── Config — loaded from .env (never hardcode secrets here) ─────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")    # set in .env
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # set in .env
EVENING_HOUR     = int(os.getenv("EVENING_HOUR",   "20"))
EVENING_MINUTE   = int(os.getenv("EVENING_MINUTE", "0"))


# ══════════════════════════════════════════════════════════════════════════
# CORE SEND
# ══════════════════════════════════════════════════════════════════════════

def telegram_configured() -> bool:
    return bool(TELEGRAM_TOKEN.strip()) and bool(TELEGRAM_CHAT_ID.strip())


def telegram_send(text: str) -> tuple:
    """Send a message. Returns (success: bool, detail: str)."""
    if not REQUESTS_AVAILABLE:
        return False, "requests not installed.  pip install requests"
    if not telegram_configured():
        return False, "Fill in TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in telegram_bot.py"
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, "Sent successfully!"
        data = resp.json()
        return False, f"Telegram error {resp.status_code}: {data.get('description', resp.text)}"
    except requests.exceptions.ConnectionError:
        return False, "No internet connection."
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════
# MESSAGE BUILDERS
# ══════════════════════════════════════════════════════════════════════════

def build_restock_message(threshold: int = 2) -> str:
    items = get_restock_list(threshold)
    if not items:
        return "✅ All items are well stocked!"
    lines = [f"🛒 *Restock List* (qty below {threshold}):\n"]
    for it in items:
        lines.append(f"  • {it.name} — only {it.quantity} left ({it.storage})")
    return "\n".join(lines)


def build_expiry_message(within_days: int = 3) -> str:
    items = get_expiring_items(within_days)
    if not items:
        return f"✅ No items expiring within {within_days} days."
    lines = [f"⏰ *Expiry Warning* (within {within_days} days):\n"]
    for it, d in items:
        if d < 0:
            label = f"expired {abs(d)} day(s) ago"
        elif d == 0:
            label = "expires TODAY"
        else:
            label = f"expires in {d} day(s)"
        lines.append(f"  • {it.name} ({it.storage}) — {label}")
    return "\n".join(lines)


def build_evening_prompt() -> str:
    today = date.today().strftime("%A, %d %B %Y")
    return (
        f"🌙 *Good evening!* ({today})\n\n"
        "What did you eat today? Open the app and log your meals.\n\n"
        "Example:\n"
        "_Breakfast: poha, chai_\n"
        "_Lunch: dal rice, salad_\n"
        "_Dinner: roti sabzi_"
    )


# ══════════════════════════════════════════════════════════════════════════
# SCHEDULER
# ══════════════════════════════════════════════════════════════════════════

class EveningScheduler:
    """
    Wraps APScheduler to send the evening prompt daily at a set time.
    Usage:
        sched = EveningScheduler()
        sched.start(hour=20, minute=0)
        sched.reschedule(hour=21, minute=30)
        sched.stop()
    """
    def __init__(self):
        self._scheduler = None

    def start(self, hour: int = EVENING_HOUR, minute: int = EVENING_MINUTE):
        if not SCHEDULER_AVAILABLE:
            return False
        self._scheduler = BackgroundScheduler(daemon=True)
        self._scheduler.add_job(
            self._send_evening,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="evening_reminder",
        )
        self._scheduler.start()
        return True

    def reschedule(self, hour: int, minute: int):
        if not self._scheduler:
            return self.start(hour, minute)
        try:
            self._scheduler.reschedule_job(
                "evening_reminder",
                trigger="cron",
                hour=hour,
                minute=minute,
            )
            return True
        except Exception as e:
            print(f"[scheduler] reschedule error: {e}")
            return False

    def stop(self):
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass

    @staticmethod
    def _send_evening():
        telegram_send(build_evening_prompt())
