"""
main.py
Entry point — run this to start the app.

    python main.py

Everything lives in:
    database.py              — DB models + session
    inventory.py             — inventory CRUD
    scan.py                  — camera + Ollama vision
    recipes_recommendation.py — recipe logic + AI suggest
    telegram_bot.py          — Telegram alerts + scheduler
    nutrition_calculator.py  — meal log + nutrition estimate
    fridge.py                — full UI (imports all the above)
"""

import sys
import os

# Add parent directory to path so we can import shared modules (database, inventory, etc.)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fridge import FridgeApp

if __name__ == "__main__":
    app = FridgeApp()
    app.mainloop()
