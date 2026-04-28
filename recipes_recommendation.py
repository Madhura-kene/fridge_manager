"""
recipes_recommendation.py
Recipe CRUD, exact-match suggestions, and Ollama AI recipe suggestions.
Imported by fridge.py for both Recipe tabs.
"""

import json
import re
import threading

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from database import session, Recipe, Inventory

# ── Config ─────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434"
OLLAMA_LLM = "llama3"


# ══════════════════════════════════════════════════════════════════════════
# EXACT-MATCH RECIPE HELPERS
# ══════════════════════════════════════════════════════════════════════════

def suggest_recipes(filter_storage: str = "Both") -> list:
    """Return [(dish, required_set)] for recipes where ALL ingredients are in stock."""
    inv = session.query(Inventory)
    if filter_storage == "Fridge":
        inv = inv.filter(Inventory.storage == "Fridge")
    elif filter_storage == "Freezer":
        inv = inv.filter(Inventory.storage == "Freezer")
    available = {row.name.strip().lower() for row in inv if row.quantity > 0}
    suggestions = []
    for r in session.query(Recipe):
        required = {x.strip().lower() for x in r.ingredients.split(",") if x.strip()}
        if required.issubset(available):
            suggestions.append((r.dish, required))
    return suggestions


def get_all_recipes() -> list:
    return session.query(Recipe).all()


def add_recipe(dish: str, ingredients: str) -> Recipe:
    r = Recipe(dish=dish.strip(), ingredients=ingredients.strip())
    session.add(r)
    session.commit()
    return r


def delete_recipe_by_id(recipe_id: int) -> bool:
    r = session.query(Recipe).filter_by(id=recipe_id).first()
    if r:
        session.delete(r)
        session.commit()
        return True
    return False


def find_recipe_by_name(name: str):
    r = session.query(Recipe).filter(Recipe.dish == name).first()
    if not r:
        r = session.query(Recipe).filter(
            Recipe.dish.like(f"{name.split(' (')[0]}%")).first()
    return r


# ══════════════════════════════════════════════════════════════════════════
# AI RECIPE SUGGESTION  (Ollama llama3, DB-only)
# ══════════════════════════════════════════════════════════════════════════

def ollama_is_running() -> bool:
    if not REQUESTS_AVAILABLE:
        return False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def ai_recipe_suggest(available: list, filter_storage: str = "Both") -> str:
    """
    Ask llama3 which DB recipes can be made or almost made.
    The FULL recipe list is injected into the prompt — model cannot
    invent any dish not already in the database.
    Returns plain text for display.
    """
    if not REQUESTS_AVAILABLE:
        return "requests not installed.  pip install requests"

    db_recipes = session.query(Recipe).all()
    if not db_recipes:
        return "No recipes in the database.\nAdd some in the Recipe Suggestions tab."

    recipe_lines = "\n".join(
        f"  - {r.dish}: needs [{r.ingredients}]" for r in db_recipes
    )
    avail_str = ", ".join(available) if available else "nothing"

    prompt = (
        "You are a kitchen assistant. "
        "The list below is the COMPLETE and ONLY set of recipes in the system. "
        "You must NEVER suggest, mention, or invent any recipe not in this list.\n\n"
        f"RECIPES IN SYSTEM (only these exist):\n{recipe_lines}\n\n"
        f"INGREDIENTS CURRENTLY AVAILABLE ({filter_storage}): {avail_str}\n\n"
        "Instructions:\n"
        "1. Section 'READY TO COOK': list every recipe where ALL ingredients are available. "
        "If none, write: None.\n"
        "2. Section 'ALMOST READY': list recipes missing only 1 or 2 ingredients. "
        "For each, state exactly which are missing. If none, write: None.\n"
        "3. Do NOT mention any recipe not in the system list.\n"
        "4. Be concise. Plain text only, no markdown."
    )

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_LLM, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "No response.").strip()
    except requests.exceptions.ConnectionError:
        return "Could not connect to Ollama.\nRun: ollama serve"
    except Exception as e:
        return f"Ollama error: {e}"
