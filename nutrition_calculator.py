"""
nutrition_calculator.py
Meal logging, daily nutrition summary, 7-day history,
and Ollama llama3 calorie/protein estimation.
Imported by fridge.py for the Nutrition tab.
"""

import json
import re
from datetime import date, datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from database import session, MealLog

# ── Config ─────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434"
OLLAMA_LLM = "llama3"


# ══════════════════════════════════════════════════════════════════════════
# OLLAMA NUTRITION ESTIMATE
# ══════════════════════════════════════════════════════════════════════════

def ollama_is_running() -> bool:
    if not REQUESTS_AVAILABLE:
        return False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def estimate_nutrition(meal_label: str, description: str) -> dict:
    """
    Ask llama3 to estimate calories and protein for the described meal.
    Forces JSON-only output and parses it robustly.
    Returns: {calories, protein_g, ai_notes, error}
    """
    if not REQUESTS_AVAILABLE:
        return {"calories": 0, "protein_g": 0, "ai_notes": "",
                "error": "requests not installed.  pip install requests"}

    prompt = (
        f"You are a nutrition assistant. "
        f"Estimate the nutritional values for this meal.\n\n"
        f"Meal type: {meal_label}\n"
        f"Description: {description}\n\n"
        "Reply with ONLY a valid JSON object — no explanation, no markdown, no extra text.\n"
        'Format exactly: {"calories": 450, "protein_g": 18, "notes": "one brief sentence"}\n\n'
        "Use realistic Indian/general food values. Estimate if unsure."
    )

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_LLM, "prompt": prompt, "stream": False},
            timeout=90,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()

        # Strip markdown fences if llama3 adds them
        raw = re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()

        # Extract first {...} block in case there is extra text
        match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        data = json.loads(raw)
        return {
            "calories":  float(data.get("calories",  0)),
            "protein_g": float(data.get("protein_g", 0)),
            "ai_notes":  str(data.get("notes", "")),
            "error":     None,
        }
    except json.JSONDecodeError:
        return {"calories": 0, "protein_g": 0,
                "ai_notes": "", "error": f"Could not parse AI response: {raw[:100]}"}
    except requests.exceptions.ConnectionError:
        return {"calories": 0, "protein_g": 0,
                "ai_notes": "", "error": "Ollama not running — run: ollama serve"}
    except Exception as e:
        return {"calories": 0, "protein_g": 0, "ai_notes": "", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════
# MEAL LOG CRUD
# ══════════════════════════════════════════════════════════════════════════

def add_meal_log(log_date, meal_label: str, description: str,
                 calories=None, protein_g=None, ai_notes=None) -> MealLog:
    entry = MealLog(
        log_date    = log_date,
        meal_label  = meal_label,
        description = description,
        calories    = calories,
        protein_g   = protein_g,
        ai_notes    = ai_notes,
    )
    session.add(entry)
    session.commit()
    return entry


def get_meal_logs_for_date(target_date) -> list:
    return (session.query(MealLog)
            .filter(MealLog.log_date == target_date)
            .order_by(MealLog.id)
            .all())


def delete_meal_log(entry_id: int) -> bool:
    e = session.query(MealLog).filter_by(id=entry_id).first()
    if e:
        session.delete(e)
        session.commit()
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════
# SUMMARIES
# ══════════════════════════════════════════════════════════════════════════

def get_daily_summary(target_date) -> dict:
    """Return {calories, protein_g, entries} for a given date."""
    entries    = get_meal_logs_for_date(target_date)
    total_cal  = sum(e.calories  or 0 for e in entries)
    total_prot = sum(e.protein_g or 0 for e in entries)
    return {"calories": total_cal, "protein_g": total_prot, "entries": entries}


def get_nutrition_history(days: int = 7) -> list:
    """Return last N days as list of dicts with date, calories, protein_g, meals."""
    today  = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d    = today - timedelta(days=i)
        summ = get_daily_summary(d)
        result.append({
            "date":      d,
            "calories":  summ["calories"],
            "protein_g": summ["protein_g"],
            "meals":     len(summ["entries"]),
        })
    return result
